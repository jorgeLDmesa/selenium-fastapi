from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
import random
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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

# Configurar el navegador
def scrape_direccion(direccion: str):
    options = webdriver.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-certificate-errors-spki-list')
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
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
        raise HTTPException(status_code=500, detail=f"Error al iniciar el navegador: {str(e)}")

    # Inicializar el diccionario para almacenar los resultados
    resultados = {}

    try:
        # Navega a la página
        driver.get('https://www.medellin.gov.co/mapgis9/mapa.jsp?aplicacion=41')
        print("Página cargada")

        # Espera que el botón "Aceptar" esté presente en el DOM y haz clic en él
        WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'button.btn.btn-siguiente.ajs-ok'))
        ).click()
        print('Botón "Aceptar" clickeado')

        # Espera a que el iframe con id "frmUtilidad53" esté presente
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, 'frmUtilidad53'))
        )
        print('iframe encontrado')

        # Cambia al contexto del iframe
        iframe = driver.find_element(By.ID, 'frmUtilidad53')
        driver.switch_to.frame(iframe)
        print('Cambio al contexto del iframe realizado.')

        # Espera a que el campo de búsqueda esté disponible dentro del iframe
        search_input = WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located((By.ID, 'strBusqueda'))
        )
        print('Campo de búsqueda encontrado')

        # Ingresa la dirección o texto que desees
        search_input.send_keys(direccion)
        print('Dirección ingresada:', direccion)

        # Espera a que el botón "Buscar" esté disponible y haz clic en él
        search_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, 'buscar'))
        )
        search_button.click()
        print('Botón "Buscar" clickeado')

        # Añadir log antes de esperar por 'strCbml'
        print('Esperando el campo "strCbml"')

        # Espera a que aparezca el campo oculto strCbml y tenga un valor
        try:
            WebDriverWait(driver, 30).until(
                lambda driver: driver.find_element(By.ID, 'strCbml').get_attribute('value') != ''
            )
            print('"strCbml" encontrado y tiene un valor.')

            # Obtiene el valor del campo strCbml
            strCbml_element = driver.find_element(By.ID, 'strCbml')
            strCbml_value = strCbml_element.get_attribute('value')
            if not strCbml_value:
                print('El campo strCbml está vacío')
                raise ValueError('El campo strCbml está vacío')
            print('Valor de strCbml:', strCbml_value)
        except Exception as e:
            print(f"Error al obtener strCbml: {e}")
            raise HTTPException(status_code=500, detail=f"Error durante el scraping: {str(e)}")

        # Itera sobre los radio buttons del 1 al 15 usando XPath
        for i in range(1, 16):
            try:
                # Construir el XPath dinámico para los radio buttons
                radio_button_xpath = f'//input[@type="radio" and @id="{i}"]'
                print(f'Intentando localizar el radio button {i} usando XPath: {radio_button_xpath}')

                # Espera a que el radio button esté presente y sea clickeable
                radio_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, radio_button_xpath))
                )
                print(f'Radio button {i} localizado y clickeable.')

                valor_radio = radio_button.get_attribute("value")
                print(f'Valor del radio button {i}: {valor_radio}')

                # Hacer clic en el radio button
                radio_button.click()
                print(f'Radio button {i} clickeado')

                # Comprobar si aparece la alerta de "no datos"
                try:
                    alert_element = driver.find_element(By.ID, 'noDatos')
                    if alert_element.is_displayed():
                        print(f'Alerta "no datos" mostrada para el radio button {i}')
                        continue
                except:
                    # Si no existe la alerta, entonces continúa
                    print(f'No se encontró alerta "no datos" para el radio button {i}')

                # Si no hay alerta, busca la tabla
                try:
                    result_table = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'table#res0'))
                    )
                    print(f'Tabla de resultados encontrada para el radio button {i}')

                    if result_table:
                        tbody = result_table.find_element(By.TAG_NAME, 'tbody')
                        rows = tbody.find_elements(By.TAG_NAME, 'tr')
                        table_data = [' | '.join([cell.text for cell in row.find_elements(By.TAG_NAME, 'td')]) for row in rows]

                        # Guardar los datos en el diccionario
                        resultados[valor_radio] = table_data
                        print(f'Datos guardados para el radio button {i}')

                except Exception as e:
                    print(f'Error al buscar tabla para el radio button {i}: {e}')

            except Exception as e:
                print(f'Error en el radio button {i}: {e}')

            # Pausa pequeña entre iteraciones
            time.sleep(0.5)

        # Convertir el diccionario a JSON
        json_resultados = json.dumps(resultados, ensure_ascii=False)
        print('Scraping completado exitosamente.')
        return json_resultados

    except HTTPException as http_exc:
        print(f"HTTPException: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        print(f"Excepción en scrape_direccion: {e}")
        raise HTTPException(status_code=500, detail=f"Error durante el scraping: {str(e)}")
    finally:
        # Cierra el navegador
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
        raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")