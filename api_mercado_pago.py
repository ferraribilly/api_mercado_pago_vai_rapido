# script.py
from flask import Flask, render_template, request, jsonify, redirect
import requests
import mercadopago
import qrcode
import io
import base64
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import threading
import socket
import os
from dotenv import load_dotenv

# 🔐 Carregar variáveis do arquivo .env
load_dotenv()

# ⚙️ Variáveis de ambiente
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE")
EMAIL_SENHA = os.getenv("EMAIL_SENHA")

api = Flask(__name__, template_folder='templates', static_folder='static')

  

# 📧 FUNÇÃO DE ENVIAR EMAIL
def enviar_email(destinatario, assunto, corpo):
    try:
        mensagem = MIMEMultipart()
        mensagem["From"] = EMAIL_REMETENTE
        mensagem["To"] = destinatario
        mensagem["Subject"] = assunto
        mensagem.attach(MIMEText(corpo, "plain"))

        servidor = smtplib.SMTP("smtp.gmail.com", 587)
        servidor.starttls()
        servidor.login(EMAIL_REMETENTE, EMAIL_SENHA)
        servidor.sendmail(EMAIL_REMETENTE, destinatario, mensagem.as_string())
        servidor.quit()
        print(f"📧 E-mail enviado para {destinatario}")
    except Exception as e:
        print(f"Erro ao enviar e-mail: {str(e)}")

def enviar_email_assincrono(destinatario, assunto, corpo):
    thread = threading.Thread(target=enviar_email, args=(destinatario, assunto, corpo))
    thread.start()

# 📥 WEBHOOK MERCADO PAGO
@api.route('/notifications/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':
        try:
            data = request.get_json()
            payment_id = data.get("data", {}).get("id")

            if payment_id:
                url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
                headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
                response = requests.get(url, headers=headers)

                if response.status_code != 200:
                    raise Exception(f"Erro na requisição ao Mercado Pago: {response.text}")

                pagamento = response.json()
                print("🔍 Dados do pagamento:", pagamento)

                status = pagamento.get("status")
                email_cliente = pagamento.get("payer", {}).get("email")

                if status == "approved":
                    enviar_email_assincrono(
                        destinatario="corporacaoenigmagames@gmail.com",
                        assunto="💰 Pagamento Aprovado",
                        corpo=f"O pagamento ID {payment_id} foi aprovado com sucesso."
                    )
                    if email_cliente:
                        enviar_email_assincrono(
                            destinatario=email_cliente,
                            assunto="✅ Pagamento Recebido",
                            corpo="Recebemos seu pagamento via PIX. Obrigado pela compra!"
                        )

            return jsonify({"status": "ok"}), 200

        except Exception as e:
            print(f"Erro ao processar o webhook: {str(e)}")
            return jsonify({"status": "erro", "message": str(e)}), 500

    return 'Webhook online (GET)', 200

  

# 💰 ROTA PRINCIPAL DE PAGAMENTO PIX
@api.route("/l")
def gerar_pagamento_pix():
    try:
        sdk = mercadopago.SDK(ACCESS_TOKEN)

        payment_data = {
            "transaction_amount": 0.01,
            "description": "Pagamento servico prestado",
            "payment_method_id": "pix",
            "payer": {
                "email": "cliente@email.com",
                "first_name": "João",
                "last_name": "Silva",
                "identification": {
                    "type": "CPF",
                    "number": "19119119100"
                },
                "address": {
                    "zip_code": "06233200",
                    "street_name": "Av. das Nações Unidas",
                    "street_number": "3003",
                    "neighborhood": "Bonfim",
                    "city": "Osasco",
                    "federal_unit": "SP"
                }
            }
        }

        payment_response = sdk.payment().create(payment_data)

        if payment_response["status"] != 201:
            raise Exception(f"Erro ao criar pagamento: {payment_response.get('message', 'Erro desconhecido')}")

        payment = payment_response["response"]
        qr_link = payment["point_of_interaction"]["transaction_data"]["ticket_url"]

        qr = qrcode.make(qr_link)
        buffer = io.BytesIO()
        qr.save(buffer, format="PNG")
        img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return render_template("pix.html", qr_code=img_base64, link=qr_link)

    except Exception as e:
        print(f"Erro ao gerar pagamento PIX: {str(e)}")
        return "Erro ao gerar pagamento", 500

# ✅ TELAS DE REDIRECIONAMENTO
@api.route("/pagamento/aprovado")
def pagamento_aprovado():
    return render_template("aprovado.html")

@api.route("/pagamento/erro")
def pagamento_erro():
    return render_template("erro.html")


@api.route('/')
def teste():
    return('teste')

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 4000))
    api.run(host='0.0.0.0', port=port)

