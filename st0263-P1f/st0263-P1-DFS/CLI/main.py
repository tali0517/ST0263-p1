import grpc
import os
import sys
from dotenv import load_dotenv
from pathlib import Path
import getpass  # Para manejar contraseñas

# Añadimos el directorio proto
project_root = Path(__file__).parent.parent / 'proto'
sys.path.append(str(project_root))
import dfs_pb2_grpc
import dfs_pb2

# Simulamos una base de datos de usuarios y contraseñas
USERS_DB = {
    "user": "123",
    "user2": "password2"
}

class CLIInterface:
    def __init__(self, name_node_url):
        self.name_node_url = name_node_url
        self.authenticated_user = None  # Para almacenar el usuario autenticado

    def clearScreen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def continueText(self):
        input("Press Enter to continue...")
        self.clearScreen()

    def authenticate(self):
        """Función para autenticación de usuario"""
        print("Welcome to DFS Server P1 - User Authentication")
        username = input("Enter your username: ")
        password = getpass.getpass("Enter your password: ")

        # Verificamos el usuario en la base de datos simulada
        if username in USERS_DB and USERS_DB[username] == password:
            print(f"Authentication successful! Welcome, {username}.")
            self.authenticated_user = username  # Guardamos el usuario autenticado
            self.continueText()
        else:
            print("Authentication failed. Invalid username or password.")
            self.authenticated_user = None
            self.continueText()

    def cli(self):
        # Autenticación antes de permitir el acceso a las funcionalidades del CLI
        self.authenticate()
        if not self.authenticated_user:
            print("Access denied.")
            return

        while True:
            self.clearScreen()
            print(f"Welcome to DFS Server P1, {self.authenticated_user}")
            print("1. Download a file")
            print("2. Upload a file")
            print("3. Search a file")
            print("4. List files")
            print("5. Exit program")
            selection = input("Enter Selection: ")

            if selection == "1":
                self.getFile()
            elif selection == "2":
                self.uploadFile()
            elif selection == "3":
                self.findFile(input("Enter exact file name: "))
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
                            print(f"File '{file_name}' successfully downloaded.")
                else:
                    print("File not found at any DataNode.")
        except Exception as e:
            print(f"Error during download: {str(e)}")

    def ReadFiles(self, filepath, chunk_size=1024):
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
                print(f"The file '{file_name}' was found at DataNodes:")
                for address in response.nodeAddresses:
                    print(address)
            else:
                print(f"The file '{file_name}' was not found")

    def listLocalFiles(self, directory="files"):
        print("Available files:")
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
                    print(f"File uploaded successfully to {len(response.conns)} DataNodes.")
                else:
                    print("Error: Ensure that at least 2 DataNodes are available.")
        except Exception as e:
            print(f"Error during file upload: {str(e)}")

    def listFiles(self):
        with grpc.insecure_channel(self.name_node_url) as chan:
            stub = dfs_pb2_grpc.dfsStub(chan)
            request = dfs_pb2.EmptyMessage()
            response = stub.ListFiles(request)

        if response.status == 200:
            print("Files:")
            print(response.files)
        else:
            print("Error listing files.")
            print("Status code: ", response.status)


if __name__ == "__main__":
    load_dotenv()
    namenode = str(os.getenv("namenode")).encode('utf-8')
    cli = CLIInterface(namenode)
    cli.cli()
