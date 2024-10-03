# ST0263-p1

# Distributed File System (DFS)

- Simon Betancur Bedoya
- Esteban Sierra Patiño
- Daniel Cano Perez
- Miguel Angel Cabrera Osorio

## Introduction
Este proyecto implementa una versión básica de un sistema de archivos distribuido (DFS) usando gRPC en Python. El sistema está diseñado para almacenar archivos en múltiples nodos de datos mientras administra los metadatos de los archivos a través de un solo nameNode. Permite a los usuarios cargar, descargar, buscar y listar archivos dentro del sistema distribuido.


## Instalacion
Para configurar el sistema de archivos distribuido, siga estos pasos:

- Asegúrese de que Python 3.6+ esté instalado en su sistema.
- Clona el repositorio en tu máquina local.
-  Instale los paquetes de Python necesarios:
   
        pip install -r requirements.txt


## Como se usa?

### Inicializar el Name Node

Primero debemos entrar a la carpeta del nameNode

        cd .\NameNodeLeader\

Ya dentro de la carpeta podemos ejecutar su archivo main 

        python .\main.py

### Inicializando los Data Node

Primero debemos entrar a la carpeta de cada uno de los data nodes, tenemos la oportunidad de ejecutar hasta 3 simultaneos!!

        cd .\DataNode\ 
        cd .\DataNode2\ 
        cd .\DataNode3\ 

Ya dentro de la carpeta podemos ejecutar su archivo main 

        python .\main.py


### Inicializar el CLI

Primero debemos entrar a la carpeta del nameNode

        cd .\CLI\

Ya dentro de la carpeta podemos ejecutar su archivo main 

        python .\main.py

## Opciones del programa

Si ejecutamos los componentes en orden correcto 

1. nameNode
2. Datanodes que deseemos
3. CLI

En la interfaz terminal del CLI tendremos las siguentes opciones 

![imagen](https://github.com/sebastianvelezg/st0263-P1-DFS/blob/main/assets/imagen-menu-ppal.jpg)

Y podremos seleccionar el numero segun como busquemos interactuar con el sistema 


## Ejemplo practico 

Cuando levantamos el programa correctamente podemos seleccionar alguna de estas 5 opciones 

        1. Download a file
        2. Upload a file
        3. Search a file
        4. List files
        5. Exit program

### Download a file
Si seleccionamos la primera opcion que es para descargar un archivo recibiremos la siguente interaccion



Tendremos un listado de los archivos disponibles en los datanodes y mediante el numero podemos descargar el que deseemos y este quedara grabado en la carpeta /download dentro de la carpeta del CLI y nos confirmara la interfaz que el archivo se descargo satisfactorio y en cual datanode fue el origen



### Upload a file

Cuando queremos montar un archivo de manera distribuida a los datanodes seleccionaremos la opcion 2 del menu

Que nos listara los archivos disponibles para montar que se encuentran en la carpeta /files dentro de la carpeta CLI.

Cuando seleccionamos un archivo que deseamos nos confirmara que el archivo se pudo cargar y en la terminal de los data nodes podemos saber donde se montaron, se montara el archivo de manera distribuida a 2 datanodes pero no 2 veces a uno mismo 

### Search a file

Cuando queremos buscar un archivo principalmente para saber en cuales datanodes se ubica usaremos la opcion 3 y al seleccionarlo nos despliega el menu donde no pedira el nombre del archivo y si lo encuentra nos devolvera en cuales datanodes se ubica (Minimo 2)


### List files

Esta opcion es la mas simple pero igual de importante que las anteriores ya que nos va a listar todos los archivos que hemos montado anteriormente en nuestro sistema de archivos distribuidos









        
