import grpc
import os
from concurrent import futures
import requests
import re
from dotenv import load_dotenv

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent / 'proto'

sys.path.append(str(project_root))
import dfs_pb2_grpc
import dfs_pb2


class CLIInterface:
    def __init__(self, name_node_url):
        self.name_node_url = name_node_url

    def clearScreen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def continueText(self):
        input("Press Enter to continue...")
        self.clearScreen()

    def cli(self):
        while True:
            self.clearScreen()
            print("----------------------------------")
            print("Welcome to DFS Server P1")
            print("----------------------------------")
            print("Select an option:")
            print("----------------------")
            print("1. Download a file")
            print("2. Upload a file")
            print("3. Search a file")
            print("4. List files")
            print("5. Exit program")
            print("----------------------------------")
            selection = input("Enter Selection: ")
            print("----------------------------------")

            if selection == "1":
                self.getFile()
            elif selection == "2":
                self.uploadFile()
            elif selection == "3":
                self.findFile(input("Enter exact file name:: "))
            elif selection == "4":
                self.listFiles()
            elif selection == "5":
                print("Exiting program...")
                break
            else:
                print("Invalid option. Try again!")

            self.continueText()

    def getFile(self):
        try:
          
            with grpc.insecure_channel(self.name_node_url) as chan:
                stub = dfs_pb2_grpc.dfsStub(chan)
                list_response = stub.ListFiles(dfs_pb2.EmptyMessage())
                if list_response.status == 200:
                    print("Available files:")
                    for idx, file_name in enumerate(list_response.files, 1):
                        print(f"{idx}. {file_name}")
                else:
                    print("No files available")
                    return

            file_idx = int(input("Select a file: ")) - 1
            if file_idx < 0 or file_idx >= len(list_response.files):
                print("Invalid selection.")
                return
            file_name = list_response.files[file_idx]

            
            with grpc.insecure_channel(self.name_node_url) as chan:
                stub = dfs_pb2_grpc.dfsStub(chan)
                download_response = stub.NameNodeDownload(dfs_pb2.DownloadFileRequest(fileName=file_name))
                if download_response.status == 200 and download_response.conns:
                    selected_data_node = download_response.conns[0]
                    print(f"Downloading file from DataNode: {selected_data_node}")

           
                    with grpc.insecure_channel(selected_data_node) as dataNodeChan:
                        dataNodeStub = dfs_pb2_grpc.dfsStub(dataNodeChan)
                        filepath = "downloads/" + file_name
                        with open(filepath, mode="wb") as f:
                            for entry_response in dataNodeStub.DownloadFile(dfs_pb2.DownloadFileRequest(fileName=file_name)):
                                f.write(entry_response.chunk_data)
                            print(f"File '{file_name}' successfully downloaded from DataNode: {selected_data_node}.")
                else:
                    print("Dont found file at any DataNode .")
        except Exception as e:
            print(f"Error during download: {str(e)}")


    def ReadFiles(self,filepath, chunk_size=1024):
        _, filename = os.path.split(filepath)
        yield dfs_pb2.UploadFileRequest(fileName=filename)
        with open(filepath, mode="rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if chunk:
                    entry_request = dfs_pb2.UploadFileRequest(chunk_data=chunk)
                    yield entry_request
                else:
                    return      

    def findFile(self, file_name):
        with grpc.insecure_channel(self.name_node_url) as chan:
            stub = dfs_pb2_grpc.dfsStub(chan)
            response = stub.FindFile(dfs_pb2.FindFileRequest(fileName=file_name))
            if response.status == 200:
                print(f"The File '{file_name}' was found at datanodes:")
                for address in response.nodeAddresses:
                    print(address)
            else:
                print(f"The file '{file_name}' was not found")

    def listLocalFiles(self, directory="files"):
        print("Available files")
        files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
        files_dict = {i + 1: f for i, f in enumerate(files)}
        return files_dict

    def uploadFile(self):
        try:
            files_dict = self.listLocalFiles("files")  
            for idx, file_name in files_dict.items():
                print(f"{idx}. {file_name}")
            file_idx = int(input("Select a file to upload: "))
            if file_idx in files_dict:
                file_path = os.path.join("files", files_dict[file_idx]) 
            else:
                print("Invalid selection")
                return

            with grpc.insecure_channel(self.name_node_url) as chan:
                stub = dfs_pb2_grpc.dfsStub(chan)
                response = stub.NameNodeUpload(dfs_pb2.EmptyMessage())
                if response.status == 200 and len(response.conns) > 0:
                    for dataNode in response.conns:
                        with grpc.insecure_channel(dataNode) as dataNodeChan:
                            dataNodeStub = dfs_pb2_grpc.dfsStub(dataNodeChan)
                            dataNodeStub.UploadFile(self.ReadFiles(file_path))
                    print(f"File uploaded successfully to {len(response.conns)} data Nodes.")
                else:
                    print("Error: The file could not be loaded. Make sure at least 2 data nodes are available.")
                    return
        except Exception as e:
            print(f"Error: An exception occurred while uploading the file - {str(e)}")

    def listFiles(self):
        with grpc.insecure_channel(self.name_node_url) as chan:
            stub = dfs_pb2_grpc.dfsStub(chan)
            request = dfs_pb2.EmptyMessage()
            response = stub.ListFiles(request)

        if response.status == 200:
            print("Files:")
            print(response.files)
        else:
            print("Error: Can not list the files")
            print("Status code: ", response.status)


if __name__ == "__main__":
    load_dotenv()
    namenode = str(os.getenv("namenode")).encode('utf-8')
    print(namenode)
    cli = CLIInterface(namenode)
    cli.cli()