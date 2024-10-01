import grpc
from dotenv import load_dotenv
import os
import sys
import time
from concurrent import futures
from os.path import isfile, join, exists
from os import listdir, makedirs
from threading import Thread
from pathlib import Path

proto_directory = Path(__file__).parent.parent / 'proto'
sys.path.insert(0, str(proto_directory))

import dfs_pb2_grpc
import dfs_pb2

HEARTBEAT_INTERVAL = 10
BLOCK_SIZE = 1024 * 1024  # 1MB tamaño del bloque, configurable
FILES_DIR = "files"  # Directorio para almacenar bloques

# Lista de DataNodes para replicación
datanodes = ['127.0.0.1:50052', '127.0.0.1:50053', '127.0.0.1:50054']  # Modifica según los DataNodes disponibles

def listFiles():
    """Lista los archivos almacenados en el directorio local 'files/'"""
    if not exists(FILES_DIR):
        makedirs(FILES_DIR)
    files = [f for f in listdir(FILES_DIR) if isfile(join(FILES_DIR, f))]
    return files

def distribute_block_to_datanodes(block_data, block_name, file_name):
    """
    Distribuye un bloque de archivo a dos DataNodes: uno como líder y otro como seguidor.
    """
    leader_node, follower_node = choose_datanodes(datanodes)

    # Enviar el bloque al líder
    send_block_to_datanode(leader_node, block_data, block_name, file_name, is_leader=True)

    # Enviar el bloque al seguidor
    send_block_to_datanode(follower_node, block_data, block_name, file_name, is_leader=False)

def choose_datanodes(datanodes):
    """
    Elige dos DataNodes de la lista para almacenar un bloque.
    """
    # Simplemente devuelve los dos primeros DataNodes de la lista para este ejemplo.
    return datanodes[0], datanodes[1]

def send_block_to_datanode(datanode_address, block_data, block_name, file_name, is_leader):
    """
    Envía un bloque a un DataNode utilizando gRPC.
    """
    try:
        # Convertir el bytearray a bytes antes de enviar
        block_data = bytes(block_data)

        # Crear un canal gRPC con el DataNode
        with grpc.insecure_channel(datanode_address) as channel:
            stub = dfs_pb2_grpc.dfsStub(channel)
            
            # Crear la solicitud
            request = dfs_pb2.UploadBlockRequest(
                fileName=file_name,
                blockName=block_name,
                chunk_data=block_data,  # Asegurarse de que sea tipo bytes
                is_leader=is_leader
            )

            # Enviar el bloque
            response = stub.UploadBlock(request)
            
            if response.status == 200:
                print(f"Bloque {block_name} enviado con éxito a {datanode_address} (Líder: {is_leader})")
            else:
                print(f"Error al enviar el bloque {block_name} a {datanode_address}: status {response.status}")
    
    except Exception as e:
        print(f"Error al enviar el bloque a {datanode_address}: {e}")

class Files(dfs_pb2_grpc.dfsServicer):
    def __init__(self, namenode, datanode):
        self.namenode = namenode
        self.datanode = datanode

    def ListFiles(self, request, context):
        try:
            files = listFiles()
            print("ListFiles Request")
            response = dfs_pb2.ListFilesResponse(files=files, status=200)
        except:
            response = dfs_pb2.ListFilesResponse(status=500)
        return response

    def DownloadFile(self, request, context):
        file_path = os.path.join(FILES_DIR, request.fileName)
        if os.path.exists(file_path):
            with open(file_path, 'rb') as file:
                while True:
                    chunk_data = file.read(1024) 
                    if not chunk_data:
                        break
                    yield dfs_pb2.DownloadFileResponse(chunk_data=chunk_data)
        else:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details('File not found')

    def UploadBlock(self, request, context):
        """
        Recibe un bloque de archivo y lo almacena localmente en este DataNode.
        """
        block_name = request.blockName
        file_path = os.path.join(FILES_DIR, block_name)
        print(f"Recibiendo bloque: {block_name} en {self.datanode}")

        try:
            # Verifica si el directorio existe, si no lo crea
            if not exists(FILES_DIR):
                makedirs(FILES_DIR)

            # Guardar el bloque en el directorio
            with open(file_path, 'wb') as block_file:
                block_file.write(request.chunk_data)
            
            print(f"Bloque {block_name} guardado correctamente en {self.datanode}")
            return dfs_pb2.UploadBlockResponse(status=200)
        except Exception as e:
            print(f"Error al guardar el bloque {block_name}: {e}")
            return dfs_pb2.UploadBlockResponse(status=500)

    def UploadFile(self, request_iterator, context):
        data = bytearray()
        print("UPLOAD Request")

        for request in request_iterator:
            if request.fileName:
                file_name = request.fileName
                print(f"Uploading: {request.fileName}")
                continue
            data.extend(request.chunk_data)

        # Dividir el archivo en bloques
        blocks = [data[i:i+BLOCK_SIZE] for i in range(0, len(data), BLOCK_SIZE)]

        # Guardar los bloques en DataNodes
        for i, block in enumerate(blocks):
            block_name = f"{file_name}_block_{i}"
            # Aquí distribuyes cada bloque a los DataNodes
            distribute_block_to_datanodes(block, block_name, file_name)

        return dfs_pb2.EmptyMessage()

def sendHeartbeat(namenode, datanode):
    """
    Envía un heartbeat periódico al NameNode para indicar que este DataNode sigue activo.
    """
    with grpc.insecure_channel(namenode) as chan:
        stub = dfs_pb2_grpc.dfsStub(chan)
        while True:
            try:
                request = dfs_pb2.NameNodeRequest(conn=datanode, files=listFiles())
                stub.NameNodeConnection(request)
                print("Heartbeat sent")
            except Exception as e:
                print(f"Failed to send heartbeat: {e}")
            time.sleep(HEARTBEAT_INTERVAL)

def createServer(namenode, datanode):
    print(f"Conectando al NameNode en {namenode}")
    with grpc.insecure_channel(namenode) as chan:
        stub = dfs_pb2_grpc.dfsStub(chan)
        request = dfs_pb2.NameNodeRequest(conn=datanode, files=listFiles())
        response = stub.NameNodeConnection(request)
        if response.status == 200:
            print("Conexión al NameNode exitosa")
    server = grpc.server(futures.ThreadPoolExecutor())
    dfs_pb2_grpc.add_dfsServicer_to_server(Files(namenode, datanode), server)
    port = 80082
    server.add_insecure_port('[::]:' + str(port))
    server.start()
    print(f"DataNode server started, port: {port}")

    heartbeat_thread = Thread(target=sendHeartbeat, args=(namenode, datanode), daemon=True)
    heartbeat_thread.start()

    server.wait_for_termination()

def main():
    load_dotenv()
    namenode = os.getenv("namenode")
    datanode2 = os.getenv("datanode2")
    createServer(namenode, datanode2)

if __name__ == "__main__":
    main()
