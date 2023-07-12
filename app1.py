from flask import Flask, render_template, request, redirect, url_for
from binance.exceptions import BinanceAPIException
from binance.client import Client
from mysql.connector import Error
from werkzeug.utils import secure_filename
from datetime import datetime
from flask_socketio import SocketIO
import clienteDAO, webview, os, ast, smtplib, email.message, hashlib, random, time, logging

app = Flask(__name__)
uploads_dir = os.path.join(app.static_folder, 'uploads')
log_dir = os.path.join(app.static_folder, "funcionamento.log")
try:
    os.remove(log_dir)
except:
    pass
logging.basicConfig(filename=log_dir, encoding='utf-8', level=logging.DEBUG)

client = None
email_cod  = None
todos  = clienteDAO.get_todos()
dia10  = clienteDAO.get_dia10()
dia15  = clienteDAO.get_dia15()
dia20  = clienteDAO.get_dia20()
dia30  = clienteDAO.get_dia30()
cliente_selecionado = ""
id_clientes = []
codigo = []
usr_cod = None
erro_pagamentos = -1

# route -> ... .com/home
socketio = SocketIO(app, cors_allowed_origins='*')
window = webview.create_window("Sistema depositos", app, min_size=(1100,600))

@app.route("/")
def ini():
    return redirect(url_for('login'))


@app.route("/login", methods=['GET','POST'])
def login():
    logging.debug("entrou na função login")
    global client, email_cod
    if client != None:
        return redirect(url_for('home'))

    erro_code = 0
    if request.method == 'POST' and request.form.get("chave") != None:
        chave_api     = request.form.get("chave")
        chave_secreta = request.form.get("chaveSecreta")
        email_cod = request.form.get("email")

        client = Client(chave_api, chave_secreta)
        try:
            client.get_account_status()
        except BinanceAPIException as e:
            logging.warning("aconteceu algum erro no login: " + str(e))
            erro_code = e.code
            client = None 
        else:
            logging.info("login efetuado")
            return redirect(url_for('home'))

    return render_template("login.html", erro_code=erro_code)


@app.route("/home", methods=['GET','POST'])
def home():
    logging.debug("entrou na função home")
    global client, todos, dia10, dia15, dia20, dia30, id_clientes, cliente_selecionado
    saldoBTC = 0
    convercao_USDT = 0
    convercao_BRL  = 0
    if client == None:
        return redirect(url_for('login'))

    if request.method == 'POST':
        if request.form.get('sair') == '-1':
            client = None
            email_cod = None
            return redirect(url_for('login'))
        
        if request.form.get('pagina') == '0':
            return redirect(url_for('add'))

        if request.form.get('pagina') == '1':
            return redirect(url_for('pesquisar'))

        if request.form.get('pagina') == '2':
            return redirect(url_for('historico'))

        if request.form.get('pagina') == '3':
            id_clientes = request.form.get("id_clientes").split(",")
            return redirect(url_for('confirmar_pagamento'))
        
        if 'arquivo' in request.files:
            logging.debug("tentativa de importar banco de dados dos clientes")
            arq = request.files['arquivo']

            final_dir = os.path.join(uploads_dir,"tmp_banco_de_dados.dbjb")
            arq.save(final_dir)

            try:
                new_arq = open(final_dir,"rt", encoding="utf8")
                dados_str = new_arq.read()

                dados = []
                dados_str = dados_str.split("§")
                dados_str.pop()
                for linha_str in dados_str:
                    linha = linha_str.split("¬")
                    linha.pop()
                    dados.append(linha)
                
                clienteDAO.importar_dados(dados)
                atualiza_dados()
            except Exception as e:
                logging.warning("erro na importação do BD:",e)
            else:
                logging.info("sucesso na importação do BD")
            finally:
                new_arq.close()
                os.remove(final_dir)
                return redirect(url_for('home'))

        if request.form.get('id') != None:
            cliente_selecionado = clienteDAO.get_cliente(request.form.get('id'))
            return redirect(url_for('cliente'))
    
    # corrigir erro do tempo: APIError(code=-1021): Timestamp for this request was 1000ms ahead of the server's time.
    try:
        saldoBTC = client.get_asset_balance("BTC")['free']
        BTC_USDT_preco = client.get_avg_price(symbol="BTCUSDT")['price']
        BTC_BRL_preco  = client.get_avg_price(symbol="BTCBRL")['price']
        convercao_USDT = float(saldoBTC) * float(BTC_USDT_preco)
        convercao_BRL  = float(saldoBTC) * float(BTC_BRL_preco)
    except BinanceAPIException as e:
        logging.warning("erro ao coletar as cotações: " + str(e))

    return render_template("home.html", saldoBTC=str(saldoBTC),convercao_BRL="R$%.2f" % convercao_BRL,convercao_USDT="U$%.2f" % convercao_USDT, todos=todos, dia10=dia10, dia15=dia15, dia20=dia20, dia30=dia30)

@app.route("/add", methods=['GET','POST'])
def add():
    logging.debug("entrou na função add")
    if client == None:
        return redirect(url_for('login'))
    

    confirmacao = "0"
    if request.method == 'POST':
        if request.form.get("voltar") == "0":
            return redirect(url_for('home'))

        else:
            nome = request.form.get("nome")
            email = request.form.get("email")
            carteira = request.form.get("hash_carteira")
            valor = request.form.get("valor_contrato")
            valor = valor.replace(".","").replace(",",".")
            dia_pagamento = request.form.get("dia_pagamento")

            try:
                clienteDAO.cadastrar_cliente(nome,carteira,valor,dia_pagamento,email)
            except Error as e:
                logging.warning("erro ao tentar cadastrar um cliente: " + str(e))
                confirmacao="-1"
                if e.sqlstate == "23000":
                    confirmacao=e.sqlstate
            else:            
                logging.info("sucesso ao tentar cadastrar um cliente")
                atualiza_dados()
                confirmacao="1"

    return render_template("adicionar.html", confirmacao=confirmacao)

@app.route("/pesquisar", methods=['GET','POST'])
def pesquisar():
    logging.debug("entrou na função pesquisar")
    if client == None:
        return redirect(url_for('login'))

    pesquisa = []

    if request.method == 'POST':
        if request.form.get("voltar") == "0":
            return redirect(url_for('home'))

        if request.form.get('id') != None:
            global cliente_selecionado
            cliente_selecionado = clienteDAO.get_cliente(request.form.get('id'))
            return redirect(url_for('cliente'))

        nome = request.form.get("nome-pesquisa")
        pesquisa = clienteDAO.pesquisar_cliente(nome)

    return render_template("pesquisar.html", pesquisa = pesquisa)

@app.route("/cliente", methods=['GET','POST'])
def cliente():
    logging.debug("entrou na função cliente")
    if client == None:
        return redirect(url_for('login'))
    
    global cliente_selecionado

    if request.method == 'POST':
        if request.form.get("voltar") == "0":
            return redirect(url_for('home'))
    
        if request.form.get("acao") == "0":
            nome = request.form.get("nome")
            email = request.form.get("email")
            carteira = request.form.get("hash_carteira")
            valor = request.form.get("valor_contrato")
            valor = valor.replace(".","").replace(",",".")
            dia_pagamento = request.form.get("dia_pagamento")
            id = request.form.get("id");
    
            try:
                clienteDAO.atualizar_cliente(nome,carteira,valor,dia_pagamento,email,id)
            except Exception as e:
                logging.warning("erro ao tentar atualizar um cliente: " + str(e))
                return render_template("cliente.html", confirmacao="-1")
            else:
                logging.info("sucesso ao tentar atualizar um cliente")
            finally:            
                atualiza_dados()
                cliente_selecionado = clienteDAO.get_cliente(id)

        if request.form.get("acao") == "1":
            id = request.form.get("id");
            try:
                clienteDAO.deletar_cliente(id)
            except Exception as e:
                logging.warning("erro ao tentar deletar um cliente " + str(e))
                return render_template("cliente.html", confirmacao="-1")
            else:
                logging.info("sucesso ao tentar deletar um cliente")
            finally:            
                atualiza_dados()
                return redirect(url_for('home'))

    return render_template("cliente.html", cliente_selecionado = cliente_selecionado, confirmacao="0")


@app.route("/efetuando_pagamentos", methods=['GET','POST'])
def efetuando_pagamentos():
    logging.debug("entrou na função efetuando_pagamentos")
    if request.form.get("acao") == "0":
        return redirect(url_for("pagamento_realizado"))
    
    return render_template("efetuando_pagamentos.html")


@app.route("/confirmar_pagamento", methods=['GET','POST'])
def confirmar_pagamento():
    logging.debug("entrou na função confirmar_pagamentos")
    if client == None:
        return redirect(url_for('home'))   

    if request.form.get("pagina") == "0":
        return redirect(url_for("home"))

    global codigo, usr_cod
    tempo_atual = time.time()
    tempo_total = -1
    tempo_restante = -1

    if len(codigo) == 2:
        tempo_total = int(tempo_atual - codigo[1])
        tempo_restante = 60 - tempo_total
        if tempo_total >= 60:
            codigo = []
            usr_cod = None
            tempo_restante = -1

    cod_digitado = request.form.get("codigo")
    if cod_digitado != None:
        result = hashlib.md5(cod_digitado.encode())
        result = result.digest()
        
        if len(codigo) == 2:
            if result == codigo[0]:
                logging.info("código de confirmação correto")
                usr_cod = cod_digitado
                socketio.start_background_task(pagar)
                return redirect(url_for("efetuando_pagamentos"))
            else:
                logging.warning("código de confirmação incorreto")
                return render_template("confirmar_pagamento.html", erro="1" ,tempo_max = tempo_restante)
        else:
            return render_template("confirmar_pagamento.html", erro="1" ,tempo_max = tempo_restante)

    return render_template("confirmar_pagamento.html", erro="-1", tempo_max = tempo_restante)


def pagar():
    logging.debug("entrou na função dpagar")
    global id_clientes, erro_pagamentos
    
    BTC_BRL_preco = client.get_avg_price(symbol="BTCBRL")['price']
    for i in range(0,len(id_clientes),2):
        cliente_pagar = clienteDAO.get_cliente(id_clientes[i])
        try:
            # client.withdraw(
            #     coin="BTC",
            #     network="BSC",
            #     address=cliente_pagar[1],
            #     amount=round((float(id_clientes[i+1])/float(BTC_BRL_preco)),8)
            # )
            # for j in range(10000000):
            a = 1
        except BinanceAPIException as e:
            logging.warning("erro ao realizar o pagamento de " + cliente_pagar[0] + ": " + str(e))
            erro_pagamentos = 0
            socketio.emit('dados_pagamentos', {'nome': cliente_pagar[0], 'valor': id_clientes[i+1], 'status': '-1', 'total':int(len(id_clientes)/2), 'index':int(i/2)})
            socketio.sleep(1)
            clienteDAO.registrar_historico(cliente_pagar[0],cliente_pagar[1],id_clientes[i+1],round((float(id_clientes[i+1])/float(BTC_BRL_preco)),8),-1)
        else:
            logging.info("sucesso ao realizar o pagamento de" + cliente_pagar[0])
            erro_pagamentos = -1
            clienteDAO.pagar(id_clientes[i])
            socketio.emit('dados_pagamentos', {'nome': cliente_pagar[0], 'valor': id_clientes[i+1], 'status': '0', 'total':int(len(id_clientes)/2), 'index':int(i/2)})
            socketio.sleep(1)   
            clienteDAO.registrar_historico(cliente_pagar[0],cliente_pagar[1],id_clientes[i+1],round((float(id_clientes[i+1])/float(BTC_BRL_preco)),8),0)
    
    atualiza_dados()
    return 


@app.route("/pagamento_realizado", methods=["GET","POST"])
def pagamento_realizado():
    logging.debug("entoru na função pagamento_realizado")
    if client == None:
        return redirect(url_for('home')) 
    
    if request.form.get("pagina") == "0":
        return redirect(url_for('home'))

    if request.form.get("pagina") == "1":
        return redirect(url_for('historico'))

    global erro_pagamentos        

    return render_template("pagamento_realizado.html", erro=erro_pagamentos)


@app.route("/historico", methods=["GET","POST"])
def historico():
    logging.debug("entoru na função historico")
    if client == None:
        return redirect(url_for('home')) 
    
    if request.form.get("voltar") == "0":
        return redirect(url_for('home'))
    
    return render_template("historico.html")

@app.route("/pesquisar_historico", methods=["GET","POST"])
def pesquisar_historico():
    logging.debug("entoru na função pagamentos pesquisar_historico")
    html = ""
    if request.method == "POST":
        data = request.data.decode("utf-8")

        historico = clienteDAO.pesquisar_historico(data)

        if(len(historico) > 0):
            for pagamento in historico:
                data_hr = pagamento[4].strftime("%d/%m/%Y") + " " + str(pagamento[5])
                status = "<font color='#02bc7d'>Sucesso</font>"
                if pagamento[6] == -1:
                    status = "<font color='#fd6e5e'>Falha</font>"

                conversao_BRL = str("%.2f" % float(pagamento[2])).replace(".",",")

                html += """
                    <div class="tentativa-pagamento">
                        <div class="primeira-linha">
                            <div class="historico-nome">""" + pagamento[0] + """</div>
                            <div class="historico-pagamento-BRL">R$ """ + conversao_BRL + """</div>
                            <div class="historico-data-horario">""" + data_hr + """</div>
                        </div>
                        <div class="segunda-linha">
                            <div class="historico-carteira">""" + pagamento[1] + """</div>
                            <div class="historico-pagamento-BTC">BTC """ + pagamento[3] + """</div>
                            <div class="historico-status">""" + status + """</div>
                        </div>
                        <div class="status" style="display: none;">""" + str(pagamento[6]) + """</div>
                    </div>
                """
        else:
            html = """<div class="nenhum-resultado">Nenhum dado referente a essa data</div>"""

    return html

@app.route("/gerar_codigo")
def gerar_codigo():
    logging.debug("entrou na função gerar código")
    global codigo, email_cod
    random.seed(datetime.now().strftime("%Y%m%d%H%M%S"))
    cod = str(random.randrange(1, 10**6)).zfill(6)

    corpo_email = """ 
        <html xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
        <head>
            <title>
            </title>
            <!--[if !mso]><!-->
            <meta http-equiv="X-UA-Compatible" content="IE=edge">
            <!--<![endif]-->
            <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style type="text/css">
            #outlook a {
                padding:0;
            }
            body {
                margin:0;
                padding:0;
                -webkit-text-size-adjust:100%;
                -ms-text-size-adjust:100%;
            }
            table, td {
                border-collapse:collapse;
                mso-table-lspace:0pt;
                mso-table-rspace:0pt;
            }
            img {
                border:0;
                height:auto;
                line-height:100%;
                outline:none;
                text-decoration:none;
                -ms-interpolation-mode:bicubic;
            }
            p {
                display:block;
                margin:13px 0;
            }
            </style>
            <!--[if mso]>
        <noscript>
        <xml>
        <o:OfficeDocumentSettings>
        <o:AllowPNG/>
        <o:PixelsPerInch>96</o:PixelsPerInch>
        </o:OfficeDocumentSettings>
        </xml>
        </noscript>
        <![endif]-->
            <!--[if lte mso 11]>
        <style type="text/css">
        .mj-outlook-group-fix { width:100% !important; }
        </style>
        <![endif]-->
            <style type="text/css">
            @media only screen and (min-width:480px) {
                .mj-column-per-100 {
                width:100% !important;
                max-width: 100%;
                }
                .mj-column-per-50 {
                width:50% !important;
                max-width: 50%;
                }
            }
            </style>
            <style media="screen and (min-width:480px)">
            .moz-text-html .mj-column-per-100 {
                width:100% !important;
                max-width: 100%;
            }
            .moz-text-html .mj-column-per-50 {
                width:50% !important;
                max-width: 50%;
            }
            </style>
            <style type="text/css">
            @media only screen and (max-width:480px) {
                table.mj-full-width-mobile {
                width: 100% !important;
                }
                td.mj-full-width-mobile {
                width: auto !important;
                }
            }
            </style>
            <style type="text/css">
            :root {
                color-scheme: light !important;
                supported-color-schemes: light !important;
            }
            @media only screen and (min-width:480px) {
                body:not(.gjs-dashed) .hidden-desktop {
                display: none !important;
                }
                div.mj-group-full-width {
                width: 100% !important;
                max-width: 100% !important;
                }
            }
            @media only screen and (max-width:480px) {
                body:not(.gjs-dashed) .hidden-mobile {
                display: none !important;
                }
            }
            </style>
            <meta name="color-scheme" content="light only">
            <meta name="supported-color-schemes" content="light">
        </head>
        <body style="word-spacing:normal;background-color:#efefef;">
            <div style="background-color:#efefef;">
            <!--[if mso | IE]><table align="center" border="0" cellpadding="0" cellspacing="0" class="" role="presentation" style="width:600px;" width="600" ><tr><td style="line-height:0px;font-size:0px;mso-line-height-rule:exactly;"><![endif]-->
            <div style="margin:0px auto;width:600px;height:83px;background-color:#1e2026;display: flex;align-items:center;justify-content:center;">
                <font color="#F1C018" style="margin-top: 30px;margin-left: 235px;"><b style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: large;">Pagamentos JB</b></font>
            </div>
            <!--[if mso | IE]></td></tr></table><table align="center" border="0" cellpadding="0" cellspacing="0" class="" role="presentation" style="width:600px;" width="600" bgcolor="#ffffff" ><tr><td style="line-height:0px;font-size:0px;mso-line-height-rule:exactly;"><![endif]-->
            <div style="background:#ffffff;background-color:#ffffff;margin:0px auto;max-width:600px;">
                <table align="center" border="0" cellpadding="0" cellspacing="0" role="presentation" style="background:#ffffff;background-color:#ffffff;width:100%;">
                <tbody>
                    <tr>
                    <td style="direction:ltr;font-size:0px;padding:5px 5px 5px 5px;text-align:center;">
                        <!--[if mso | IE]><table role="presentation" border="0" cellpadding="0" cellspacing="0"><tr><td class="" width="600px" ><table align="center" border="0" cellpadding="0" cellspacing="0" class="" role="presentation" style="width:590px;" width="590" ><tr><td style="line-height:0px;font-size:0px;mso-line-height-rule:exactly;"><![endif]-->
                        <div style="margin:0px auto;max-width:590px;">
                        <table align="center" border="0" cellpadding="0" cellspacing="0" role="presentation" style="width:100%;">
                            <tbody>
                            <tr>
                                <td style="direction:ltr;font-size:0px;padding:5px 5px 5px 5px;text-align:center;">
                                <!--[if mso | IE]><table role="presentation" border="0" cellpadding="0" cellspacing="0"><tr><td class="" style="vertical-align:top;width:580px;" ><![endif]-->
                                <div class="mj-column-per-100 mj-outlook-group-fix" style="font-size:0px;text-align:left;direction:ltr;display:inline-block;vertical-align:top;width:100%;">
                                    <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="vertical-align:top;" width="100%">
                                    <tbody>
                                        <tr>
                                        <td align="left" class="mj-text" style="font-size:0px;padding:5px 5px 10px 5px;word-break:break-word;" dir="ltr">
                                            <div style="font-family:BinancePlex,Arial,PingFangSC-Regular,'Microsoft YaHei',sans-serif;font-size:20px;font-weight:900;line-height:25px;text-align:left;color:#000000;">Confirmação de pagamento
                                            </div>
                                        </td>
                                        </tr>
                                        <tr>
                                        <td align="left" class="mj-text" style="font-size:0px;padding:5px 5px 5px 5px;word-break:break-word;" dir="ltr">
                                            <div style="font-family:BinancePlex,Arial,PingFangSC-Regular,'Microsoft YaHei',sans-serif;font-size:14px;line-height:20px;text-align:left;color:#000000;">Seu código de confirmação
                                            </div>
                                        </td>
                                        </tr>
                                        <tr>
                                        <td align="left" class="mj-text" style="background:#ffffff;font-size:0px;padding:5px 5px 5px 5px;word-break:break-word;" dir="ltr">
                                            <div style="font-family:BinancePlex,Arial,PingFangSC-Regular,'Microsoft YaHei',sans-serif;font-size:18px;line-height:30px;text-align:left;color:rgb(240, 185, 11);">
                                            <b>""" + cod + """</b>
                                            </div>
                                        </td>
                                        </tr>
                                        <tr>
                                        <td align="left" class="mj-text" style="font-size:0px;padding:5px 5px 5px 5px;word-break:break-word;" dir="ltr">
                                            <div style="font-family:BinancePlex,Arial,PingFangSC-Regular,'Microsoft YaHei',sans-serif;font-size:14px;line-height:20px;text-align:left;color:#000000;">O código de confirmação será válido por 1 minuto. Por favor não compartilhar este código com ninguém.
                                            </div>
                                        </td>
                                        </tr>
                                        <tr>
                                        <td align="left" class="mj-text" style="font-size:0px;padding:5px 5px 5px 5px;word-break:break-word;" dir="ltr">
                                            <div style="font-family: BinancePlex, Arial, PingFangSC-Regular, &quot;Microsoft YaHei&quot;, sans-serif; font-size: 14px; line-height: 20px; text-align: left; color: rgb(0, 0, 0);">
                                            <div draggable="true">Não reconhece esta atividade? Verifique se você está logado no sitema e procure deslogar o mais rápido possível.&nbsp;</div>
                                            <div>
                                                <br>
                                            </div>
                                            <div>
                                                <i>&nbsp;Esta é uma mensagem automática, não responda.
                                                </i>
                                            </div>
                                            </div>
                                        </td>
                                        </tr>
                                    </tbody>
                                    </table>
                                </div>
                                <!--[if mso | IE]></td></tr></table><![endif]-->
                                </td>
                            </tr>
                            </tbody>
                        </table>
                        </div>
                        <!--[if mso | IE]></td></tr></table></td></tr></table><![endif]-->
                    </td>
                    </tr>
                </tbody>
                </table>
            </div>
            <!--[if mso | IE]></td></tr></table><table align="center" border="0" cellpadding="0" cellspacing="0" class="" role="presentation" style="width:600px;" width="600" bgcolor="#ffffff" ><tr><td style="line-height:0px;font-size:0px;mso-line-height-rule:exactly;"><![endif]-->
            
            <!--[if mso | IE]></td></tr></table><![endif]-->
            </div>
        </body>
        </html>
    """

    result = hashlib.md5(cod.encode())
    codigo.append(result.digest())
    codigo.append(time.time())
    del cod
    del result

    msg = email.message.Message()
    msg['Subject'] = "[Sistema Pagamentos] Confirmação de pagamento " + str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    msg['From'] = "sistemapagamentosjb@gmail.com"
    msg['To'] = email_cod
    senha = "eabtagvzvgznpmjm"

    msg.add_header('Content-Type', 'text/html')
    # msg.add_header('Content-Transfer-Encoding','base64')
    msg.set_payload(corpo_email)

    s = smtplib.SMTP('smtp.gmail.com: 587')
    s.starttls()
    s.login(msg["From"],senha)
    s.sendmail(msg["From"],[msg["To"]], msg.as_string().encode('utf-8'))
    logging.info("sucesso ao enviar email com codigo de confirmação")
    del corpo_email
    return "nothing"


def atualiza_dados():
    global todos, dia10, dia15, dia20, dia30
    todos  = clienteDAO.get_todos()
    dia10  = clienteDAO.get_dia10()
    dia15  = clienteDAO.get_dia15()
    dia20  = clienteDAO.get_dia20()
    dia30  = clienteDAO.get_dia30()

if __name__ == "__main__":
    app.run(debug=True)
    # webview.start()