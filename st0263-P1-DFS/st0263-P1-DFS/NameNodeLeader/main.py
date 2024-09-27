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

nodes = []
files = {}
class Files(dfs_pb2_grpc.dfsServicer):        
    def NameNodeConnection(self, request, context):
        if request.conn and request.conn not in nodes:
            nodes.append(request.conn)
            files[request.conn] = request.files
            print(f"-- Conection established: {request.conn}")
        return dfs_pb2.StatusMessage(status=200)

    def NameNodeDownload(self, request, context):
        fileName = request.fileName
        nodeAddresses = [node for node, fileList in files.items() if fileName in fileList]
        
        if nodeAddresses:
            selected_node = random.choice(nodeAddresses)
            return dfs_pb2.DataNodeResponse(conns=[selected_node], status=200)
        else:
            return dfs_pb2.DataNodeResponse(status=404)

    def NameNodeUpload(self, request, context):
        if len(nodes) < 2:
            print("Not enough DataNode available.")
            return dfs_pb2.DataNodeResponse(status=400)

        selected_nodes = random.sample(nodes, 2)
        response = dfs_pb2.DataNodeResponse(conns=selected_nodes, status=200)
        return response

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
        for node, last_heartbeat in list(nodes.items()):
            if time.time() - last_heartbeat > DISCONNECT_THRESHOLD:
                print(f"-- Connection lost: {node}")
                disconnectedDataNodes.append(node)
                del files[node]
        for node in disconnectedDataNodes:
            del nodes[node]
        time.sleep(HEARTBEAT_INTERVAL)
    
def startServer():
    server = grpc.server(futures.ThreadPoolExecutor())
    dfs_pb2_grpc.add_dfsServicer_to_server(Files(),server)

    port = 50051
    server.add_insecure_port('[::]:'+str(port))
    server.start()
    print("server started, port: "+str(port))
    server.wait_for_termination()

def main():
    startServer()
    

if __name__ == "__main__":
    main()