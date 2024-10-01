import grpc
import sys
import random
from concurrent import futures
import time
from threading import Thread
from pathlib import Path

proto_directory = Path(__file__).parent.parent / 'proto'

sys.path.append(str(proto_directory))
import dfs_pb2_grpc
import dfs_pb2

HEARTBEAT_INTERVAL = 10
DISCONNECT_THRESHOLD = 30

# Diccionario para almacenar nodos y sus métricas (carga, espacio disponible, última señal)
nodes = {}
files = {}

class Files(dfs_pb2_grpc.dfsServicer):        
    def NameNodeConnection(self, request, context):
        # Registro de DataNodes con métricas
        if request.conn and request.conn not in nodes:
            nodes[request.conn] = {
                'files': request.files,
                'last_heartbeat': time.time(),
                'load': len(request.files),  # Usamos la cantidad de archivos como proxy de carga
                'available_space': 1000  # Puedes implementar un sistema real para calcular espacio disponible
            }
            files[request.conn] = request.files
            print(f"-- Connection established: {request.conn}")

        return dfs_pb2.StatusMessage(status=200)

    def NameNodeDownload(self, request, context):
        fileName = request.fileName
        nodeAddresses = [node for node, node_info in files.items() if fileName in node_info]
        
        if nodeAddresses:
            selected_node = random.choice(nodeAddresses)
            return dfs_pb2.DataNodeResponse(conns=[selected_node], status=200)
        else:
            return dfs_pb2.DataNodeResponse(status=404)

    def NameNodeUpload(self, request, context):
        if len(nodes) < 2:
            print("Not enough DataNodes available.")
            return dfs_pb2.DataNodeResponse(status=400)

        # Seleccionar dos nodos con menor carga
        selected_nodes = self.select_best_datanodes(2)
        if selected_nodes:
            response = dfs_pb2.DataNodeResponse(conns=selected_nodes, status=200)
            return response
        else:
            return dfs_pb2.DataNodeResponse(status=500)

    def select_best_datanodes(self, num_nodes=2):
        """
        Selecciona los mejores DataNodes según la menor carga (nodos con menos archivos).
        """
        # Ordenar los DataNodes por carga (número de archivos o bloques)
        sorted_nodes = sorted(nodes.items(), key=lambda item: item[1]['load'])
        
        # Seleccionar los nodos con menor carga
        return [node for node, info in sorted_nodes[:num_nodes]]

    def ListFiles(self, request, context):
        print("LIST Request")
        listFiles = set()
    
        for i in files:
            for file in files[i]:
                listFiles.add(file)

        uniqueListFiles = list(listFiles)
        print(uniqueListFiles)
        return dfs_pb2.ListFilesResponse(files=uniqueListFiles, status=200)
    
    def FindFile(self, request, context):
        fileName = request.fileName
        nodeAddresses = []
        for node, fileList in files.items():
            if fileName in fileList:
                nodeAddresses.append(node)
        if nodeAddresses:
            return dfs_pb2.FindFileResponse(nodeAddresses=nodeAddresses, status=200)
        else:
            return dfs_pb2.FindFileResponse(status=404)

def checkHeartbeat():
    while True:
        disconnectedDataNodes = []
        current_time = time.time()

        for node, node_info in list(nodes.items()):
            if current_time - node_info['last_heartbeat'] > DISCONNECT_THRESHOLD:
                print(f"-- Connection lost: {node}")
                disconnectedDataNodes.append(node)
                del files[node]

        for node in disconnectedDataNodes:
            del nodes[node]

        time.sleep(HEARTBEAT_INTERVAL)
    
def startServer():
    server = grpc.server(futures.ThreadPoolExecutor())
    dfs_pb2_grpc.add_dfsServicer_to_server(Files(), server)

    port = 80080
    server.add_insecure_port('[::]:'+str(port))
    server.start()
    print("server started, port: "+str(port))
    server.wait_for_termination()

def main():
    # Iniciar el servidor
    startServer()

if __name__ == "__main__":
    main()
