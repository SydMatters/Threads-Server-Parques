import mysql.connector
from mysql.connector import Error

def choose_option_from_menu():
    print("Seleccione una opcion: \n1. Crear registro\n2. Leer registros\n3. Actualizar registro\n4. Eliminar registro\n0. salir")
    chosen_option = int(input("Ingrese el numero de la opcion deseada: "))
    return chosen_option

def create_record(cursor, connection):
    already_exists = True
    while already_exists:
        user_name = input("Ingrese el nombre del jugador: ")
        cursor.execute("SELECT user_name FROM players WHERE user_name = %s", (user_name,))
        query_result = cursor.fetchone()
        if query_result is not None:
            print("El nombre de usuario ya existe. Por favor, elija otro.")
        else:
            print("Nombre de usuario disponible.")
            already_exists = False
    password = input("Ingrese la contraseña del jugador: ")
    insert_query = "INSERT INTO players (user_name, password, statistics) VALUES (%s, %s, %s)"
    cursor.execute(insert_query, (user_name, password, 0))
    connection.commit()
    print("Registro insertado con éxito.")
    
def read_records(cursor):
    cursor.execute("SELECT * FROM players;")
    records = cursor.fetchall()
    for record in records:
        print(record[0], "tiene un total de victorias de", record[2])
        
def update_record_statistics(cursor, connection):
    user_name_to_update = input("Digite el nombre del usuario que desea actualizar las estadísticas: ")
    query = "SELECT user_name, statistics FROM players WHERE user_name = %s"
    cursor.execute(query, (user_name_to_update,))
    result = cursor.fetchone()
    if result is None:
        print("El nombre de usuario no existe.")
    else:
        updated_statistics = result[1] + 1
        cursor.execute("UPDATE players SET statistics = %s WHERE user_name = %s", (updated_statistics, user_name_to_update))
        connection.commit()
        print("Registro actualizado con éxito.")
        
def update_record_name(cursor, connection):
    user_name_to_update = input("Digite el nombre del usuario que desea actualizar: ")
    query = "SELECT user_name FROM players WHERE user_name = %s"
    cursor.execute(query, (user_name_to_update,))
    if cursor.fetchone() is None:
        print("El nombre de usuario no existe.")
    else:
        new_user_name = input("Digite el nuevo nombre de usuario: ")
        cursor.execute("UPDATE players SET user_name = %s WHERE user_name = %s", (new_user_name, user_name_to_update))
        connection.commit()
        print("Registro actualizado con éxito.")

def delete_record(cursor, connection):
    user_name_to_delete = input("Digite el nombre del usuario que desea eliminar: ")
    query = "SELECT user_name FROM players WHERE user_name = %s"
    cursor.execute(query, (user_name_to_delete,))
    query = cursor.fetchone()
    if query is None:
        print("El nombre de usuario no existe.")
    else:
        cursor.execute("DELETE FROM players WHERE user_name = %s", (user_name_to_delete,))
        connection.commit()
        print("Registro eliminado con éxito.")

def crud_operations():
    try:
        connection = mysql.connector.connect(user="root", host="localhost", database="registered_users")
        cursor = connection.cursor()
        chosen_option = 1
        while chosen_option != 0:
            chosen_option = choose_option_from_menu()
            if chosen_option == 1:
                create_record(cursor, connection)
            elif chosen_option == 2:
                read_records(cursor)
            elif chosen_option == 3:
                update_record_name(cursor, connection)
            elif chosen_option == 4:
                delete_record(cursor, connection)
            chosen_option = int(input("digite 1 si quiere realizar otra operacion o digite 0 para salir: "))
    except Error as e:
        print(f"Error al conectar a la base de datos: {e}")
    finally:
        if connection.is_connected():
            connection.close()
            print("Conexión cerrada")

def main():
    crud_operations()

if __name__ == "__main__":
    main()

