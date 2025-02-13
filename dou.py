import requests
from bs4 import BeautifulSoup
import json
from datetime import date
from babel.dates import get_day_names
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

load_dotenv()

def raspa_dou():
    print('Raspando as notícias do dia...')
    page = requests.get('http://www.in.gov.br/leiturajornal')
    soup = BeautifulSoup(page.text, 'html.parser')
    conteudo = json.loads(soup.find("script", {"id": "params"}).text)
    print('Notícias raspadas')
    return conteudo

def formata_data():
    print('Encontrando a data...')
    data_atual = date.today()
    day_names = get_day_names('wide', locale='pt_BR')
    dia_da_semana = day_names[data_atual.weekday()]
    data_formatada = data_atual.strftime("%d/%m/%Y")
    print('Data encontrada')
    return data_formatada

def procura_termos(conteudo_raspado):
    print('Buscando palavras-chave...')
    palavras_chave = ['Inteligência Artificial', 'Data Center', 'OpenAI', 'Chatgpt', 'Anthropic', 'Claude', 'Google', 'Alphabet', 'Palantir', 'Databricks', 'Wide Labs', 'Widelabs', 'Tencent', 'Deepseek', 'NVIDIA', 'AMD', 'Azure']
    URL_BASE = 'https://www.in.gov.br/en/web/dou/-/'
    resultados_por_palavra = {palavra: [] for palavra in palavras_chave}
    nenhum_resultado_encontrado = True

    for resultado in conteudo_raspado['jsonArray']:
        item = {
            'section': 'Seção 1',
            'title': resultado['title'],
            'href': URL_BASE + resultado['urlTitle'],
            'abstract': resultado['content'],
            'date': resultado['pubDate']
        }

        for palavra in palavras_chave:
            if palavra.lower() in item['abstract'].lower():
                resultados_por_palavra[palavra].append(item)
                nenhum_resultado_encontrado = False

    if nenhum_resultado_encontrado:
        print(f'As palavras-chave não foram encontradas. Volte novamente amanhã')
        return {}
    print('Palavras-chave encontradas')
    return resultados_por_palavra

def salva_na_base(palavras_raspadas):
    if not palavras_raspadas:
        print('Sem palavras encontradas')
        return

    print('Salvando palavras na base de dados...')
    with open('credenciais.json') as f:
        credentials = json.load(f)

    conta = ServiceAccountCredentials.from_json_keyfile_dict(credentials)
    api = gspread.authorize(conta)
    planilha = api.open_by_key(os.getenv('PLANILHA'))
    sheet = planilha.worksheet('Página1')

    for palavra, lista_resultados in palavras_raspadas.items():
        for item in lista_resultados:
            data = item['date']
            titulo = item['title']
            url = item['href']
            resumo = item['abstract']
            palavra_chave = palavra
            sheet.append_row([data, palavra_chave, titulo, url, resumo])
    print('Resultados salvos')

def envia_email(palavras_raspadas):
    if not palavras_raspadas:
        print('Sem palavras encontradas')
        return

    print('Enviando e-mail...')
    smtp_server = "smtp-relay.brevo.com"
    port = 587
    email = os.getenv('EMAIL')
    password = os.getenv('SENHA_EMAIL')
    remetente = 'Busca_DOU@email.com'
    destinatarios = os.getenv('DESTINATARIOS').split(',')
    data = date.today().strftime('%d/%m/%Y')
    titulo = f'Busca DOU do dia {data}'
    html = f"""<!DOCTYPE html>
    <html>
        <head>
            <title>Busca DOU</title>
        </head>
        <body>
            <h1>Consulta ao Diário Oficial da União</h1>
            <p>As matérias encontradas no dia {data} foram:</p>
    """
    for palavra, lista_resultados in palavras_raspadas.items():
        html += f"<h2>{palavra}</h2>\n"
        if lista_resultados:
            html += "<ul>\n"
            for resultado in lista_resultados:
                html += f"<li><a href='{resultado['href']}'>{resultado['title']}</a></li>\n"
            html += "</ul>\n"
        else:
            html += "<p>Nenhum resultado encontrado para esta palavra-chave.</p>\n"

    html += "</body></html>"

    try:
        server = smtplib.SMTP(smtp_server, port)
        server.starttls()
        server.login(email, password)

        mensagem = MIMEMultipart()
        mensagem["From"] = remetente
        mensagem["To"] = ",".join(destinatarios)
        mensagem["Subject"] = titulo
        conteudo_html = MIMEText(html, "html")
        mensagem.attach(conteudo_html)

        server.sendmail(remetente, destinatarios, mensagem.as_string())
        print('E-mail enviado')
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")
    finally:
        server.quit()

if __name__ == "__main__":
    conteudo_raspado = raspa_dou()
    palavras_raspadas = procura_termos(conteudo_raspado)
    data = formata_data()
    salva_na_base(palavras_raspadas)
    envia_email(palavras_raspadas)
