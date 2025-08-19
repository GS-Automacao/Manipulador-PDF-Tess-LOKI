from PyPDF2 import PdfReader, PdfWriter
from typing import List, Dict
from time import sleep
from tqdm import tqdm
from PIL import Image
import pytesseract
import cv2 as cv
import shutil
import fitz
import os


pytesseract.pytesseract.tesseract_cmd = 'configs/tess/tesseract.exe'

all_sizes = {'Curitiba':   {(612, 792): [(125, 240, 350, 255), (505,  52, 535,  63)],
                            (596, 842): [(86, 164, 380, 172), (86, 176, 160, 186)],
                            (842, 1192): [(122, 232, 550, 244), (122, 250, 220, 262)]},
             'Salvador':   {(595, 842): [( 10, 198, 250, 208), (445,  22, 500,  32)]},
             'Sorocaba':   {(595, 842): [(135, 300, 370, 310), (260, 108, 276, 116)]},
             'Vitória':    {(596, 842): [(110, 255, 400, 270), (405,  38, 450,  50)]},

             'São-Paulo':  {'modelo1': [(100, 185, 575, 200), (66, 200, 340, 212)],
                            'modelo2': [(133, 185, 530, 196), (105, 196, 335, 207)]}
            
            }


def extract_text(path: str, config='--psm 10') -> str:
    img = cv.imread(path)
    scale_percent = 15  # Aumentar a imagem em 150%
    # Calculando o novo tamanho
    new_width = int(img.shape[1] * scale_percent)
    new_height = int(img.shape[0] * scale_percent)
    # Redimensionar a imagem proporcionalmente
    img = cv.resize(img, (new_width, new_height), interpolation=cv.INTER_LANCZOS4)
    # 1. Conversão para escala de cinza
    img = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    # Executar o OCR na imagem processada
    text = pytesseract.image_to_string(img, config=config)
    return text


def pdf_split(path: str) -> None:
    with open(path, 'rb') as file:
        pdf = PdfReader(file)
        if len(pdf.pages) > 1:
            for i, page in enumerate(pdf.pages):
                writer = PdfWriter()
                writer.add_page(page)
                with open(f'{path[:-4]}-{i}.pdf', 'wb') as output:
                    writer.write(output)


def tratar_tamanho_corte(recorte: tuple):
    """
    Essa função é responsável por dobrar
    o valor das coordenadas de corte
    caso a dimensão da pagina seja dobrada.
    Então continuará capturando a informação
    de maneira proporcional.

    Args:
        parametro1: 4-tupla com as posições do corte.
    
    Returns:
        A 4-tupla com os valores dobrados.
    """
    recorte = list(recorte)
    for pos in range(0, len(recorte)):
        recorte[pos] = recorte[pos] * 2
    
    recorte = tuple(recorte)
    return recorte


def pdf_to_img(path: str, sizes: Dict, page: int = 0) -> None:
    #a imagem2 é apenas para capturar as dimensões originais
    pdf_document = fitz.open(path)  # Abre a Nota Fiscal.
    page = pdf_document.load_page(page)  # Carrega a página.
    image = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # Converte a página num objeto de imagem.
    image2 = page.get_pixmap()  # Converte a página num objeto de imagem.
    image.save('img.jpg')  # Salva a imagem num arquivo.
    image2.save('img2.jpg')  # Salva a imagem num arquivo.
    pdf_document.close()  # Fechar o PDF para garantir que o arquivo seja liberado.
    image = Image.open('img.jpg')
    image2 = Image.open('img2.jpg')

    #EXCLUIR DPS
    # print(tratar_tamanho_imagem(image.size))
    # print(sizes)

    if image2.size in sizes:
        nome = image.crop(tratar_tamanho_corte(sizes[image2.size][0]))
        cnpj = image.crop(tratar_tamanho_corte(sizes[image2.size][1]))
    else:
        raise TypeError()
    
    nome.save('nome.jpg')
    cnpj.save('cnpj.jpg')


def pdf_to_img_sao_paulo(path: str, sizes: Dict, page: int = 0) -> None:
    pdf_document = fitz.open(path)  # Abre a Nota Fiscal.
    page = pdf_document.load_page(page)  # Carrega a página.
    image = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # Converte a página num objeto de imagem.
    image.save('img.jpg')  # Salva a imagem num arquivo.
    pdf_document.close()  # Fechar o PDF para garantir que o arquivo seja liberado.
    image = Image.open('img.jpg')
    # if image.size in sizes:
    nome = image.crop(tratar_tamanho_corte(sizes['modelo1'][0]))
    cnpj = image.crop(tratar_tamanho_corte(sizes['modelo1'][1]))
    nome2 = image.crop(tratar_tamanho_corte(sizes['modelo2'][0]))
    cnpj2 = image.crop(tratar_tamanho_corte(sizes['modelo2'][1]))
    # else:
        # raise TypeError()
    nome.save('nome.jpg')
    cnpj.save('cnpj.jpg')
    nome2.save('nome2.jpg')
    cnpj2.save('cnpj2.jpg')



def processa_nfs(cidade: str, files: List[str] = []) -> int:
    tot_pags: int = 0
    sizes = all_sizes.get(cidade, None)
    # Verifica se a cidade foi encontrada.
    if sizes is None:
        raise TypeError('Cidade não cadastrada.')
    # Lista as NFs no diretório.
    if not files:
        files = [file for file in os.listdir() if '.pdf' in file.lower()]

    print(cidade)
    sleep(0.1)
    # Renomeia as notas.
    for file in tqdm(files):
        try:
            pdf_to_img(file, sizes)
        except TypeError:
            continue
        nome: str = extract_text('nome.jpg', config='--psm 7').strip()
        cnpj: str = extract_text('cnpj.jpg', config='--psm 7 -c tessedit_char_whitelist=0123456789').strip()

        novo_nome = f'{nome} - {cnpj} NF.pdf'
        mapeamento = {
            '®': '',
            '/': '',
            '\\': '',
            '|': '',
            '”': '',
            '<': '',
            '=': ''
        }
        novo_nome = novo_nome.translate(str.maketrans(mapeamento))
        shutil.move(file, novo_nome)
    try:
        # Apaga as imagens residuais.
        os.remove('img.jpg')
        os.remove('nome.jpg')
        os.remove('cnpj.jpg')
        os.remove('img2.jpg')
    except FileNotFoundError:
        pass

    return tot_pags


def processa_nfs_sao_paulo(cidade: str, files: List[str] = []) -> int:
    tot_pags: int = 0
    sizes = all_sizes.get(cidade, None)
    # Verifica se a cidade foi encontrada.
    if sizes is None:
        raise TypeError('Cidade não cadastrada.')
    # Lista as NFs no diretório.
    if not files:
        files = [file for file in os.listdir() if '.pdf' in file.lower()]

    print(cidade)
    sleep(0.1)
    # Renomeia as notas.
    for file in tqdm(files):
        try:
            pdf_to_img_sao_paulo(file, sizes)
        except TypeError:
            continue
        nome: str = extract_text('nome.jpg', config='--psm 7').strip()
        cnpj: str = extract_text('cnpj.jpg', config='--psm 7 -c tessedit_char_whitelist=0123456789').strip()
        nome2: str = extract_text('nome2.jpg', config='--psm 7').strip()
        cnpj2: str = extract_text('cnpj2.jpg', config='--psm 7 -c tessedit_char_whitelist=0123456789').strip()

        #buscar qual dos dois cnpjs foi extraido corretamente
        cnpj = cnpj.replace(".", "").replace("/", "").replace("-", "")
        cnpj2 = cnpj2.replace(".", "").replace("/", "").replace("-", "")

        if(len(cnpj) == 14):
            pass
        elif len(cnpj2) == 14:
            nome = nome2
            cnpj = cnpj2

        novo_nome = f'{nome} - {cnpj} NF.pdf'
        shutil.move(file, novo_nome)
        
    try:
        # Apaga as imagens residuais.
        os.remove('img.jpg')
        os.remove('nome.jpg')
        os.remove('nome2.jpg')
        os.remove('cnpj.jpg')
        os.remove('cnpj2.jpg')
    except FileNotFoundError:
        pass

    return tot_pags


def processa_outras(files: List[str] = [], tipo: str = '') -> int:
    tot_pags = len(files)
    if not tipo:
        tipo = 'Vila Velha'
    if not files:
        files = [file for file in os.listdir() if '.pdf' in file.lower()]

    if tipo == 'Vila Velha':
        print('Vila Velha')
        for file in tqdm(files):
            with open(file, 'rb') as file_b:
                pdf = PdfReader(file_b).pages[0]
                rows = pdf.extract_text().split('\n')
            num_nf = rows[6].split()[-1]
            for i, row in enumerate(rows):
                if 'Nota Fiscal de Serviços' in row:
                    nome = rows[i + 1].replace('/', '')
                    break
            nome_arq = f'NF {num_nf} - {nome}.pdf'
            os.rename(file, nome_arq)
    return tot_pags


def limpa_residuos():
    files = []
    tipos = ['.jpg', '.png']
    for tipo in tipos:
        files += [file for file in os.listdir() if tipo in file.lower()]
    for file in files:
        os.remove(file)
