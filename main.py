from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import random
import traceback
import time
import re
from typing import Optional, List, Dict, Any

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todas las solicitudes de origen
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permitir todas las cabeceras
)

class DireccionInput(BaseModel):
    direccion: str

class MunicipioInput(BaseModel):
    municipio: str

class SearchInput(BaseModel):
    search_query: str
    verification_word: Optional[str] = None

class StoreDataItem(BaseModel):
    Pallet_ID: Optional[str] = None
    Item: Optional[str] = None
    Product_Class: Optional[str] = None
    Category_Code: Optional[str] = None
    Category: Optional[str] = None
    Item_Description: str
    Qty: Optional[str] = None
    Unit_Retail: Optional[str] = None
    Ext_Retail: Optional[str] = None
    Origin: Optional[str] = None
    UPC: Optional[str] = None
    TCIN: Optional[str] = None
    Brand: Optional[str] = None
    Division_Name: Optional[str] = None
    Subcategory: Optional[str] = None
    Department: Optional[str] = None

class StoreDataInput(BaseModel):
    store: str
    data: List[StoreDataItem]

def scrape_direccion(direccion: str):
    options = webdriver.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-certificate-errors-spki-list')
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
    ]

    options.add_argument(f"user-agent={random.choice(user_agents)}")
    # Iniciar el navegador
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        print("ChromeDriver iniciado correctamente.")
    except Exception as e:
        print(f"Error al iniciar ChromeDriver: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al iniciar el navegador: {str(e)}")

    resultados = {}

    try:
        driver.get('https://www.medellin.gov.co/mapgis9/mapa.jsp?aplicacion=41')
        print("Página cargada")

        WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'button.btn.btn-siguiente.ajs-ok'))
        ).click()
        print('Botón "Aceptar" clickeado')

        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, 'frmUtilidad53'))
        )
        print('iframe encontrado')

        iframe = driver.find_element(By.ID, 'frmUtilidad53')
        driver.switch_to.frame(iframe)
        print('Cambio al contexto del iframe realizado.')

        search_input = WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located((By.ID, 'strBusqueda'))
        )
        print('Campo de búsqueda encontrado')

        search_input.send_keys(direccion)
        print('Dirección ingresada:', direccion)

        search_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, 'buscar'))
        )
        search_button.click()
        print('Botón "Buscar" clickeado')

        driver.implicitly_wait(30)

        print('Esperando el campo "strCbml"')

        try:
            WebDriverWait(driver, 60).until(
                lambda driver: driver.find_element(By.ID, 'strCbml').get_attribute('value') != ''
            )
            print('"strCbml" encontrado y tiene un valor.')

            strCbml_element = driver.find_element(By.ID, 'strCbml')
            strCbml_value = strCbml_element.get_attribute('value')
            if not strCbml_value:
                print('El campo strCbml está vacío')
                raise ValueError('El campo strCbml está vacío')
            print('Valor de strCbml:', strCbml_value)
        except Exception as e:
            print(f"Error al obtener strCbml: {e}")
            traceback.print_exc()
            with open('pagina_error.html', 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            raise HTTPException(status_code=500, detail=f"Error durante el scraping: {str(e)}")

        for i in range(1, 16):
            try:
                radio_button_xpath = f'//input[@type="radio" and @id="{i}"]'
                print(f'Intentando localizar el radio button {i} usando XPath: {radio_button_xpath}')

                radio_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, radio_button_xpath))
                )
                print(f'Radio button {i} localizado y clickeable.')

                valor_radio = radio_button.get_attribute("value")
                print(f'Valor del radio button {i}: {valor_radio}')

                radio_button.click()
                print(f'Radio button {i} clickeado')

                try:
                    alert_element = driver.find_element(By.ID, 'noDatos')
                    if alert_element.is_displayed():
                        print(f'Alerta "no datos" mostrada para el radio button {i}')
                        continue
                except:
                    print(f'No se encontró alerta "no datos" para el radio button {i}')

                try:
                    result_table = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'table#res0'))
                    )
                    print(f'Tabla de resultados encontrada para el radio button {i}')

                    if result_table:
                        tbody = result_table.find_element(By.TAG_NAME, 'tbody')
                        rows = tbody.find_elements(By.TAG_NAME, 'tr')
                        table_data = [' | '.join([cell.text for cell in row.find_elements(By.TAG_NAME, 'td')]) for row in rows]
                        resultados[valor_radio] = table_data
                        print(f'Datos guardados para el radio button {i}')

                except Exception as e:
                    print(f'Error al buscar tabla para el radio button {i}: {e}')
                    traceback.print_exc()

            except Exception as e:
                print(f'Error en el radio button {i}: {e}')
                traceback.print_exc()

            time.sleep(0.5)

        json_resultados = json.dumps(resultados, ensure_ascii=False)
        print('Scraping completado exitosamente.')
        return json_resultados

    except HTTPException as http_exc:
        print(f"HTTPException: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        print(f"Excepción en scrape_direccion: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error durante el scraping: {str(e)}")
    finally:
        driver.quit()
        print("Navegador cerrado.")


@app.post("/scrape_direccion")
async def scrape_direccion_endpoint(direccion: DireccionInput):
    try:
        print(f"Solicitud recibida para scrape_direccion: {direccion.direccion}")
        resultados = scrape_direccion(direccion.direccion)
        print("Respuesta enviada exitosamente.")
        return {"resultados": resultados}
    except HTTPException as http_exc:
        print(f"HTTPException: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        print(f"Excepción no manejada: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")


def scrape_resultados_electorales(municipio: str):
    options = webdriver.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-certificate-errors-spki-list')
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument("--disable-notifications")

    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        wait = WebDriverWait(driver, 20)
        
        url = "https://resultadospreccongreso.registraduria.gov.co/senado/0"
        driver.get(url)
        
        search_input = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "downshift-0-input"))
        )
        time.sleep(3)
        search_input.clear()
        search_input.send_keys(municipio)
        time.sleep(2)
        search_input.send_keys(Keys.ARROW_DOWN)
        search_input.send_keys(Keys.ENTER)
        time.sleep(5)

        js_script = "return document.querySelectorAll('div.containerMasMenos button').length > 0;"
        wait.until(lambda driver: driver.execute_script(js_script))
        
        partidos_info = {}
        nombres_partidos = driver.find_elements(By.CLASS_NAME, "FilaTablaPartidos__NombrePartido-jcnt0x-7")
        porcentajes = driver.find_elements(By.CLASS_NAME, "porcAgr")
        votos = driver.find_elements(By.CLASS_NAME, "numAgr")
        
        for nombre, porcentaje, voto in zip(nombres_partidos, porcentajes, votos):
            partidos_info[nombre.text] = {"porcentaje": porcentaje.text, "votos": voto.text, "candidatos": []}

        botones = driver.execute_script(
            "return Array.from(document.querySelectorAll('div.containerMasMenos button'));"
        )

        for boton, partido_nombre in zip(botones, partidos_info.keys()):
            driver.execute_script("arguments[0].scrollIntoView(true);", boton)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", boton)
            
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "FilaTablaPartidos__ContainerLista-jcnt0x-3"))
            )
            
            container = driver.find_element(By.CLASS_NAME, "FilaTablaPartidos__ContainerLista-jcnt0x-3")
            candidatos = container.find_elements(By.CLASS_NAME, "FilaTablaPartidos__ElementoCandidatos-jcnt0x-5")
            
            candidatos_procesados = 0
            for candidato in candidatos:
                try:
                    nombre = candidato.find_element(By.CLASS_NAME, "FilaTablaPartidos__NombreCandidato-jcnt0x-4").text
                    porcentaje = candidato.find_element(By.CLASS_NAME, "percent").text
                    voto_cand = candidato.find_elements(By.TAG_NAME, "p")[2].text
                    
                    partidos_info[partido_nombre]["candidatos"].append({
                        "nombre": nombre,
                        "porcentaje": porcentaje,
                        "votos": voto_cand
                    })
                    
                    candidatos_procesados += 1
                    if candidatos_procesados >= 5:
                        break
                except:
                    continue
            
            driver.execute_script("arguments[0].click();", boton)
            time.sleep(0.5)

        return json.dumps(partidos_info, ensure_ascii=False)

    except Exception as e:
        print(f"Error en scrape_resultados_electorales: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error durante el scraping: {str(e)}")
    finally:
        driver.quit()

@app.post("/scrape_resultados")
async def scrape_resultados_endpoint(municipio: MunicipioInput):
    try:
        print(f"Solicitud recibida para scrape_resultados: {municipio.municipio}")
        resultados = scrape_resultados_electorales(municipio.municipio)
        return {"resultados": resultados}
    except HTTPException as http_exc:
        print(f"HTTPException: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        print(f"Excepción no manejada: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")


def scrape_google_search(search_query: str, verification_word: Optional[str] = None):
    options = webdriver.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-certificate-errors-spki-list')
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
    ]
    options.add_argument(f"user-agent={random.choice(user_agents)}")

    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        print("ChromeDriver iniciado correctamente.")
        wait = WebDriverWait(driver, 10)

        print(f"Realizando búsqueda: {search_query}")
        driver.get("https://www.google.com")
        search_box = wait.until(EC.presence_of_element_located((By.NAME, "q")))
        search_box.send_keys(search_query)
        search_box.send_keys(Keys.RETURN)
        
        print("Esperando resultados de búsqueda...")
        first_results = wait.until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#search .g a"))
        )[:2]

        first_link = first_results[0].get_attribute('href')

        if not verification_word:
            print(f"Retornando primer link: {first_link}")
            return {"status": "success", "link": first_link}
        
        print(f"Verificando palabra clave: {verification_word}")
        for i, result in enumerate(first_results, 1):
            try:
                link = result.get_attribute('href')
                print(f"Analizando link #{i}: {link}")
                result.click()
                
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                
                page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                
                if verification_word.lower() in page_text:
                    print(f"Palabra clave encontrada en link #{i}")
                    return {
                        "status": "success", 
                        "message": f"Palabra '{verification_word}' encontrada en el link #{i}", 
                        "link": link
                    }
                
                print(f"Palabra clave no encontrada en link #{i}, regresando a resultados...")
                driver.back()
                wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#search .g a")))
                
            except Exception as e:
                print(f"Error al procesar el link #{i}: {str(e)}")
                traceback.print_exc()
                continue
        
        print("Palabra clave no encontrada en ningún resultado")
        return {
            "status": "not_found",
            "message": "No se encontró la palabra clave en los resultados",
            "link": first_link
        }
        
    except Exception as e:
        print(f"Error durante el scraping: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error durante la búsqueda: {str(e)}")
    
    finally:
        driver.quit()
        print("Navegador cerrado.")

@app.post("/verify_product")
async def verify_product_endpoint(search_input: SearchInput):
    try:
        print(f"Solicitud recibida para verify_product: {search_input.search_query}")
        result = scrape_google_search(search_input.search_query, search_input.verification_word)
        print("Respuesta enviada exitosamente.")
        return result
    except HTTPException as http_exc:
        print(f"HTTPException: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        print(f"Excepción no manejada: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")


# ------------------- NUEVO ENDPOINT -------------------

def extract_image_src(driver):
    try:
        modal_div = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[jsname="figiqf"]'))
        )
        first_image = modal_div.find_element(By.TAG_NAME, "img")
        image_src = first_image.get_attribute("src")
        print(f"URL de la imagen encontrada: {image_src}")
        return image_src
    except Exception as e:
        print(f"Error al extraer la imagen: {e}")
        return None    

def search_in_google_images(query, driver):
    try:
        driver.get("https://www.google.com/imghp")
        search_box = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.NAME, "q"))
        )
        search_box.send_keys(query)
        search_box.send_keys(Keys.RETURN)
        
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "rso"))
        )

        rso_div = driver.find_element(By.ID, "rso")
        first_img = rso_div.find_element(By.TAG_NAME, "img")
        first_img.click()

        image_link = extract_image_src(driver)
        return image_link
    except Exception as e:
        print(f"Error al buscar en Google Imágenes para '{query}': {e}")
        return None

def get_costco_image_link(query, driver):
    try:
        driver.get("https://www.google.com")
        
        search_box = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.NAME, "q"))
        )
        search_box.send_keys(query)
        search_box.send_keys(Keys.RETURN)

        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h3"))
        )

        first_result = driver.find_element(By.CSS_SELECTOR, "h3")
        first_result.click()

        time.sleep(1)
        images = driver.find_elements(By.XPATH, "//img[@alt='Product Preview 1']")
        
        if not images:
            print("No se encontró 'Product Preview 1' en Costco.")
            return None
        
        largest_canvas = 0
        largest_canvas_link = None
        
        for img in images:
            src = img.get_attribute("src")
            canvas_match = re.search(r"canvas=(\d+),(\d+)", src)
            if canvas_match:
                width, height = map(int, canvas_match.groups())
                canvas_size = width * height
                if canvas_size > largest_canvas:
                    largest_canvas = canvas_size
                    largest_canvas_link = src
        
        return largest_canvas_link
    except Exception as e:
        print(f"Error al procesar el query '{query}' para Costco: {e}")
        return None

def get_amazon_image_link(query, driver):
    try:
        driver.get("https://www.google.com")
        
        search_box = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.NAME, "q"))
        )
        search_box.send_keys(query)
        search_box.send_keys(Keys.RETURN)

        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h3"))
        )

        first_result = driver.find_element(By.CSS_SELECTOR, "h3")
        first_result.click()
        time.sleep(1)

        try:
            landing_image = driver.find_element(By.XPATH, "//img[@data-a-image-name='landingImage']")
            data_dynamic_image = landing_image.get_attribute("data-a-dynamic-image")
            image_dict = json.loads(data_dynamic_image)
            
            largest_area = 0
            largest_url = None
            
            for url, dims in image_dict.items():
                w, h = dims
                area = w * h
                if area > largest_area:
                    largest_area = area
                    largest_url = url
            
            return largest_url
        except:
            print("No se encontró la imagen 'landingImage' en Amazon.")
            return None
    except Exception as e:
        print(f"Error al procesar el query '{query}' para Amazon: {e}")
        return None

def get_target_image_link(query, driver):
    try:
        driver.get("https://www.google.com")
        
        search_box = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.NAME, "q"))
        )
        search_box.send_keys(query)
        search_box.send_keys(Keys.RETURN)

        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h3"))
        )

        first_result = driver.find_element(By.CSS_SELECTOR, "h3")
        first_result.click()
        time.sleep(1)

        try:
            img = driver.find_element(By.CSS_SELECTOR, "div[tabindex='-1'] img")
            srcset = img.get_attribute("srcset")
            if not srcset:
                return img.get_attribute("src")
            
            candidates = srcset.split(",")
            max_width = 0
            best_url = None
            for candidate in candidates:
                parts = candidate.strip().split(" ")
                if len(parts) == 2:
                    url, size = parts
                    if size.endswith("w"):
                        width = int(size.replace("w", ""))
                        if width > max_width:
                            max_width = width
                            best_url = url
            return best_url if best_url else img.get_attribute("src")
        except:
            print("No se encontró la imagen en Target.")
            return None
    except Exception as e:
        print(f"Error al procesar el query '{query}' para Target: {e}")
        return None


@app.post("/get_images")
async def get_images_endpoint(payload: StoreDataInput):
    store = payload.store
    data = payload.data

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    results = []
    try:
        for item in data:
            description = item.Item_Description
            query = f"{description} {store}"
            print(f"Buscando: {query}")

            if store.lower() == "costco":
                link = get_costco_image_link(query, driver)
                if not link:
                    link = search_in_google_images(query, driver)
            elif store.lower() == "amazon":
                link = get_amazon_image_link(query, driver)
                if not link:
                    link = search_in_google_images(query, driver)
            elif store.lower() == "target":
                link = get_target_image_link(query, driver)
                if not link:
                    link = search_in_google_images(query, driver)
            else:
                # Si no es Costco, Amazon ni Target, buscar directamente en Google Images
                link = search_in_google_images(query, driver)
            
            results.append({
                "Item Description": description,
                "image_link": link
            })
    finally:
        driver.quit()

    return {"results": results}
