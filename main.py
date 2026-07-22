# main.py
import extraer_comentarios
import generar_informe
import logging

# Configurar logging para ver los mensajes de ambos scripts
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def main():
    """
    Script principal que ejecuta todo el proceso de actualización del dashboard.
    """
    logging.info("🤖 INICIANDO PROCESO DE ACTUALIZACIÓN AUTOMÁTICA...")

    try:
        # PASO 1: Ejecutar la extracción de comentarios
        extraer_comentarios.run_extraction()

        # PASO 2: Ejecutar la generación del informe HTML
        generar_informe.run_report_generation()

        logging.info("🎉 ¡PROCESO FINALIZADO CON ÉXITO!")

    except Exception as e:
        logging.error(f"❌ ERROR FATAL: El proceso principal falló.", exc_info=True)

if __name__ == "__main__":
    main()