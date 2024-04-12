import requests
from bs4 import BeautifulSoup
from datetime import datetime
from datetime import date
import json
from babel.dates import format_date, format_datetime, get_day_names
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import os

def raspa_dou():
  print('Raspando as notícias do dia...')
  page = requests.get('http://www.in.gov.br/leiturajornal')
  soup = BeautifulSoup(page.text, 'html.parser')
  conteudo = json.loads(soup.find("script", {"id": "params"}).text)
  print('Notícias raspadas')
  return conteudo
conteudo_raspado = raspa_dou()

def formata_data():
  print('Encontrando a data...')
  data_atual = date.today()
  day_names = get_day_names('wide', locale='pt_BR')
  dia_da_semana = day_names[data_atual.weekday()]
  data_formatada = data_atual.strftime("%d/%m/%Y")
  print('Data encontrada')
  return data_formatada
data = formata_data()

def procura_termos(conteudo_raspado):
  print('Buscando palavras-chave...')

  palavras_chave = ['Comunicação', 'Secretaria de Prêmios e Apostas', 'Aposta de Quota Fixa', 'Apostas', 'Cassino', 'Manipulação de Resultados',
                  'iGaming', 'Fantasy Games']
  URL_BASE = 'https://www.in.gov.br/en/web/dou/-/'
  resultados_por_palavra = {palavra: [] for palavra in palavras_chave}
  nenhum_resultado_encontrado = True  # Variável para verificar se encontrou algum resultado

  for resultado in conteudo_raspado['jsonArray']:
      item = {}
      item['section'] = 'Seção 1'
      item['title'] = resultado['title']
      item['href'] = URL_BASE + resultado['urlTitle']
      item['abstract'] = resultado['content']
      item['date'] = resultado['pubDate']

      for palavra in palavras_chave:
          if palavra.lower() in item['abstract'].lower():
              resultados_por_palavra[palavra].append(item)
              nenhum_resultado_encontrado = False  # Define como False quando ao menos um resultado é encontrado

    # Se nenhum resultado foi encontrado, exibe a mensagem e retorna um dicionário vazio
  if nenhum_resultado_encontrado:
      print(f'Não houve publicação do Diário Oficial da União no dia {data}. Volte novamente entre segunda e sexta-feira')
  print('Palavras chaves encontradas')
  return resultados_por_palavra
palavras_raspadas = procura_termos(conteudo_raspado)

def salva_na_base(palavras_raspadas):
  print('Salvando palavras na base de dados...')
  arquivo_credencials = os.getenv('CHAVE_CREDENCIAIS')
  conta = ServiceAccountCredentials.from_json_keyfile_name(arquivo_credencials)
  api = gspread.authorize(conta)
  planilha = api.open_by_key('1cSPu6t84C8j_nI6UZXzkbmCwdFPmQWeyd9giVAtzLrQ')
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
  print('Enviando e-mail...')
  smtp_server = "smtp-relay.brevo.com"
  port = 587
  email = os.getenv('EMAIL')
  password = os.getenv('SENHA_EMAIL')

  # Dados para o email que será enviado:
  remetente = os.getenv('EMAIL')
  destinatarios = os.getenv('EMAIL')
  titulo = f'Busca DOU do dia {data}'
  html = """
  <!DOCTYPE html>
  <html>
    <head>
      <title>Busca DOU</title>
    </head>
    <body>
      <h1>Consulta ao Diário Oficial da União</h1>
      """
  html += f'<p> As matérias encontradas no dia {data} foram:'

  for palavra, lista_resultados in palavras_raspadas.items():
      html += f"<h2>{palavra}</h2>\n"
      if lista_resultados:
          html += "<ul>\n"
          for resultado in lista_resultados:
              html += f"<li><a href='{resultado['href']}'>{resultado['title']}</a></li>\n"
          html += "</ul>\n"
      else:
          html += "<p>Nenhum resultado encontrado para esta palavra-chave.</p>\n"

  html += "</body>\n</html>"

  print('Iniciando conexão com o servidor...')
  server = smtplib.SMTP(smtp_server, port)  # Inicia a conexão com o servidor
  server.starttls()  # Altera a comunicação para utilizar criptografia
  server.login(email, password)  # Autentica

  # Preparando o objeto da mensagem ("documento" do email):
  mensagem = MIMEMultipart()
  mensagem["From"] = remetente
  mensagem["To"] = ",".join(destinatarios)
  mensagem["Subject"] = titulo
  conteudo_html = MIMEText(html, "html")  # Adiciona a versão em HTML
  mensagem.attach(conteudo_html)

  # Enviando o email pela conexão já estabelecida:
  server.sendmail(remetente, destinatarios, mensagem.as_string())
  print('E-mail enviado')




