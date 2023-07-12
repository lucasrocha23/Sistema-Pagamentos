import mysql.connector
from mysql.connector import Error
from datetime import datetime


def conectarBD():
    try:
        connection = mysql.connector.connect(host='localhost',
                                            database='bdjbinvestimentos',
                                            user='root',
                                            password='abcd1234')

        if connection.is_connected():
            return connection
                          
    except Error as e:
        print("Error while connecting to MySQL", e)


def cadastrar_cliente(nome, carteira, valor, dia , email):
    connection = conectarBD()
    cursor = connection.cursor()

    id  = str(datetime.now().strftime("%Y%m%d%H%M%S"))
    sql = "INSERT INTO bdjbinvestimentos.cliente (nome, carteira,valor_contrato,dia_pagamento, email, id) VALUES ('" + nome + "', '" + carteira + "', '" + valor + "', '" + dia + "', '" + email + "', '" + id + "')"
    print(sql)
    cursor.execute(sql)

    connection.commit()
    connection.close()



def atualizar_cliente(nome, carteira, valor, dia, email, id):
    connection = conectarBD()
    cursor = connection.cursor()

    print(nome)
    print(carteira)
    print(valor)
    print(dia)
    print(email)
    print(id)
    sql = "UPDATE bdjbinvestimentos.cliente SET  nome = '" + nome + "', carteira = '" + carteira + "', valor_contrato = '" + valor + "', dia_pagamento = '" + dia + "', email = '" + email + "' WHERE id = '" + id + "'"

    try:
        cursor.execute(sql)

        connection.commit()
    except:
        print("Erro ao atualizar um cliente")
    else:
        connection.close()


def deletar_cliente(id):
    connection = conectarBD()
    cursor = connection.cursor()

    sql = "DELETE FROM bdjbinvestimentos.cliente WHERE id = '" + id + "'"

    try:
        cursor.execute(sql)

        connection.commit()
    except:
        print("Erro ao deletar um cliente")
    else:
        connection.close()


def get_cliente(id):
    connection = conectarBD()
    cursor = connection.cursor()

    print(id)
    sql = "SELECT * FROM bdjbinvestimentos.cliente WHERE id = '" + id + "'"
    try:
        cursor.execute(sql)
        records = cursor.fetchall()
    except:
        print("Erro ao pegar um cliente")
    else:
        connection.close()
        return records[0]


def pesquisar_cliente(nome):
    connection = conectarBD()
    cursor = connection.cursor()

    sql = "SELECT * FROM bdjbinvestimentos.cliente WHERE nome LIKE '%" + nome + "%' ORDER BY nome"

    try:
        cursor.execute(sql)
        records = cursor.fetchall()
    except:
        print("Erro ao pesquisar um cliente")
    else:
        connection.close()
        return records

def pagar(id):
    connection = conectarBD()
    cursor = connection.cursor()

    data = datetime.now().strftime("%Y-%m-%d")
    # data = "2023-03-20"
    sql = "UPDATE bdjbinvestimentos.cliente SET ultimo_pagamento = '" + data + "' WHERE id = '" + id + "'"

    try:
        cursor.execute(sql)

        connection.commit()
    except:
        print("Erro ao registrar o pagamento de um cliente")
    else:
        connection.close()

def get_todos():
    connection = conectarBD()
    cursor = connection.cursor()
    lista  = []

    sql = "SELECT * FROM bdjbinvestimentos.cliente ORDER BY nome"

    try:
        cursor.execute(sql)
        records = cursor.fetchall()
    except:
        print("Erro ao pegar todos os clientes")
    else:
        connection.close()

        return records

def get_dia10():
    connection = conectarBD()
    cursor = connection.cursor()
    lista  = []

    sql = "SELECT * FROM bdjbinvestimentos.cliente WHERE dia_pagamento = 10 ORDER BY nome"

    try:
        cursor.execute(sql)
        records = cursor.fetchall()
    except:
        print("Erro ao pegar todos os clientes")
    else:
        connection.close()
        
        return records


def get_dia15():
    connection = conectarBD()
    cursor = connection.cursor()
    lista  = []

    sql = "SELECT * FROM bdjbinvestimentos.cliente WHERE dia_pagamento = 15 ORDER BY nome"

    try:
        cursor.execute(sql)
        records = cursor.fetchall()
    except:
        print("Erro ao pegar todos os clientes")
    else:
        connection.close()

        return records

def get_dia20():
    connection = conectarBD()
    cursor = connection.cursor()
    lista  = []

    sql = "SELECT * FROM bdjbinvestimentos.cliente WHERE dia_pagamento = 20 ORDER BY nome"

    try:
        cursor.execute(sql)
        records = cursor.fetchall()
    except:
        print("Erro ao pegar todos os clientes")
    else:
        connection.close()

        return records


def get_dia30():
    connection = conectarBD()
    cursor = connection.cursor()
    lista  = []

    sql = "SELECT * FROM bdjbinvestimentos.cliente WHERE dia_pagamento = 30 ORDER BY nome"

    try:
        cursor.execute(sql)
        records = cursor.fetchall()
    except:
        print("Erro ao pegar todos os clientes")
    else:
        connection.close()

        return records

def importar_dados(dados):
    connection = conectarBD()
    cursor = connection.cursor()

    sql  = "INSERT INTO bdjbinvestimentos.cliente (nome, carteira,valor_contrato,dia_pagamento, email, ultimo_pagamento, id) VALUES (%s, %s, %s, %s, %s, %s, %s)"
    sql2 = "UPDATE bdjbinvestimentos.cliente SET nome = %s, valor_contrato = %s, dia_pagamento = %s, email = %s, ultimo_pagamento = %s, carteira = %s WHERE id = %s"
    
    for cliente in dados:
        nome     = cliente[0]
        carteira = cliente[1]
        valor    = cliente[2]
        dia      = cliente[3]
        email    = cliente[4]
        u_dia    = cliente[5]
        id       = cliente[6]
        
        if u_dia == "None":
            u_dia = None

        try:
            cursor.execute(sql,(nome,carteira,valor,dia,email,u_dia,id))
        except Error as e:

            try:
                cursor.execute(sql2,(nome,valor,dia,email,u_dia,carteira,id))
            except Error as e2:
                print("erro 2:", e2)

    connection.commit()
    connection.close()

def registrar_historico(nome, carteira, pagamentoBRL, pagamentoBTC, status):
    connection = conectarBD()
    cursor = connection.cursor()
    
    data = datetime.now().strftime("%Y-%m-%d")
    hora = datetime.now().strftime("%H:%M:%S")
    id   = str(datetime.now().strftime("%Y%m%d%H%M%S"))

    sql  = "INSERT INTO bdjbinvestimentos.historico (nome, carteira, pagamentoBRL, pagamentoBTC, data, hora, status, id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"

    cursor.execute(sql,(nome,carteira,pagamentoBRL,pagamentoBTC,data,hora,status,id))

    connection.commit()
    connection.close()

def pesquisar_historico(data):
    connection = conectarBD()
    cursor = connection.cursor()

    sql = 'SELECT * FROM bdjbinvestimentos.historico WHERE data = "' + data + '"';
    # print(sql)

    records = []
    try:
        cursor.execute(sql)
        records = cursor.fetchall()
    except Error as e:
        print("Erro ao pesquisar no historico")
        print(e)
    
    connection.commit()
    connection.close()

    return records
