import grpc
from dotenv import load_dotenv
import os
import sys
import time
from concurrent import futures
from os.path import isfile, join
from os import listdir
from threading import Thread
from pathlib import Path

proto_directory = Path(__file__).parent.parent / 'proto'

sys.path.append(str(proto_directory))
import dfs_pb2_grpc
import dfs_pb2

HEARTBEAT_INTERVAL = 10

def listFiles():
    files = [f for f in listdir("files/") if isfile(join("files/", f))]
    return files

class Files(dfs_pb2_grpc.dfsServicer):
    def __init__(self, namenode, datanode2):
        self.namenode = namenode
        self.datanode2 = datanode2

    def ListFiles(self, request, context):
        try:
            files = listFiles()
            print("ListFiles Request")
            response = dfs_pb2.ListFilesResponse(files=files,status=200)
        except:
            response = dfs_pb2.ListFilesResponse(status=500)
        return response

    def DownloadFile(self, request, context):
        file_path = os.path.join('files', request.fileName)
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

    
    def UploadFile(self, request_iterator, context):
        data = bytearray()
        filepath = 'files/'
        print("UPLOAD Request")

        for request in request_iterator:
            if request.fileName:
                filepath += request.fileName
                print("Uploading: "+request.fileName)
                continue
            data.extend(request.chunk_data)
        with open(filepath, 'wb') as f:
            f.write(data)
        
        with grpc.insecure_channel(self.namenode) as chan:
            stub = dfs_pb2_grpc.dfsStub(chan)
            request = dfs_pb2.NameNodeRequest(conn=self.datanode2,files=listFiles())
            response = stub.NameNodeConnection(request)
            if response.status == 200:
                print("Namenode success!")
        
        return dfs_pb2.EmptyMessage()

def sendHeartbeat(namenode, datanode2):
    with grpc.insecure_channel(namenode) as chan:
        stub = dfs_pb2_grpc.dfsStub(chan)
        while True:
            try:
                request = dfs_pb2.NameNodeRequest(conn=datanode2, files=listFiles())
                stub.NameNodeConnection(request)
                print("Heartbeat sent")
            except Exception as e:
                print(f"Failed to send heartbeat: {e}")
            time.sleep(HEARTBEAT_INTERVAL)

def createServer(namenode, datanode2):
    print("namenode", namenode)
    with grpc.insecure_channel(namenode) as chan:
        stub = dfs_pb2_grpc.dfsStub(chan)
        request = dfs_pb2.NameNodeRequest(conn=datanode2,files=listFiles())
        response = stub.NameNodeConnection(request)
        if response.status == 200:
            print("Namenode success!")
    server = grpc.server(futures.ThreadPoolExecutor())
    dfs_pb2_grpc.add_dfsServicer_to_server(Files(namenode, datanode2),server)
    port = 50053
    server.add_insecure_port('[::]:'+str(port))
    server.start()
    print("DataNode server started, port: "+str(port))

    heartbeat_thread = Thread(target=sendHeartbeat, args=(namenode, datanode2), daemon=True)
    heartbeat_thread.start()

    server.wait_for_termination()

def main():
    load_dotenv()
    namenode = os.getenv("namenode")
    datanode2 = os.getenv("datanode2")
    createServer(namenode, datanode2)    

if __name__ == "__main__":
    main()