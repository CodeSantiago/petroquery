#!/usr/bin/env python3
"""
Generador avanzado de documentos tecnicos O&G sinteticos para PetroQuery.
Crea 8 PDFs realistas con tablas complejas, datos numericos, y terminologia de Vaca Muerta.
"""

import os
from fpdf import FPDF

OUTPUT_DIR = "/home/sayer/Proyectos/petroquery/data/pdfs_og"
os.makedirs(OUTPUT_DIR, exist_ok=True)


class PetroPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(26, 35, 126)
        self.cell(0, 8, "PETROQUERY | DOCUMENTO TECNICO SINTETICO", align="R", ln=True)
        self.set_draw_color(255, 111, 0)
        self.line(10, 18, 200, 18)
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Pagina {self.page_no()} | CONFIDENCIAL", align="C")

    def chapter_title(self, num, title):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(26, 35, 126)
        self.cell(0, 10, f"{num}. {title}", ln=True)
        self.ln(2)

    def chapter_subtitle(self, title):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(60, 60, 60)
        self.cell(0, 8, title, ln=True)
        self.ln(1)

    def body_text(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def warning_box(self, text):
        self.set_fill_color(255, 243, 224)
        self.set_draw_color(255, 111, 0)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(255, 111, 0)
        self.cell(0, 6, "ADVERTENCIA DE SEGURIDAD", ln=True)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(80, 40, 0)
        self.multi_cell(0, 5, text, border=1, fill=True)
        self.ln(3)

    def table_row(self, cells, widths=None, bold=False, fill=False):
        self.set_font("Helvetica", "B" if bold else "", 9)
        if fill:
            self.set_fill_color(230, 230, 250)
        else:
            self.set_fill_color(255, 255, 255)
        if widths is None:
            widths = [190 / len(cells)] * len(cells)
        for text, w in zip(cells, widths):
            self.cell(w, 6, str(text), border=1, fill=True)
        self.ln()


def generate_all_pdfs():
    """Generate all 8 synthetic PDFs."""
    
    # PDF 1: Manual de Perforacion No Convencional
    pdf = PetroPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(26, 35, 126)
    pdf.cell(0, 20, "MANUAL DE PERFORACION NO CONVENCIONAL", align="C", ln=True)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Cuenca Neuquina - Vaca Muerta", align="C", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 10, "Rev. 0 | Abril 2024 | YPF S.A. / Tecpetrol S.A.", align="C", ln=True)
    pdf.ln(20)

    pdf.chapter_title("1", "Resumen Ejecutivo")
    pdf.body_text("El presente manual establece los procedimientos tecnicos para la perforacion de pozos no convencionales en la formacion Vaca Muerta, Cuenca Neuquina, Argentina. Abarca desde el diseno del pozo hasta la terminacion, incluyendo fracking multietapa y control de pozos.")

    pdf.chapter_title("2", "Geologia de la Cuenca Neuquina")
    pdf.body_text("La Cuenca Neuquina es una cuenca sedimentaria de retroarco situada en el oeste de Argentina. La formacion Vaca Muerta (Tithoniano-Berriasiano) constituye la unidad generadora de hidrocarburos mas importante. Sus principales caracteristicas son: espesor 30-50m, TOC 3-8%, madurez termica en ventana de aceite a gas humedo (Ro 0.8-1.2%).")

    pdf.chapter_title("3", "Diseno de Pozos")
    pdf.chapter_subtitle("3.1 Especificaciones de Casing")
    pdf.body_text("El programa de casing tipico para pozos horizontales en Vaca Muerta es el siguiente:")
    widths = [50, 40, 40, 30, 30]
    pdf.table_row(["Casing", "Diametro", "Profundidad (m)", "Peso (ppf)", "Grado"], widths, bold=True, fill=True)
    pdf.table_row(["Conductor", '30"', "150", "310", "K-55"], widths)
    pdf.table_row(["Superficial", '13 3/8"', "1,200", "68", "K-55"], widths)
    pdf.table_row(["Intermedio", '9 5/8"', "2,800", "53.5", "P-110"], widths)
    pdf.table_row(["Produccion", '7"', "3,500", "29", "P-110"], widths)
    pdf.table_row(["Liner", '5 1/2"', "4,200 - 5,800", "23", "P-110"], widths)
    pdf.ln(3)

    pdf.chapter_subtitle("3.2 Trayectoria del Pozo")
    pdf.body_text("Los pozos en Vaca Muerta tipicamente siguen una trayectoria en forma de 'J' o 'S': seccion vertical hasta ~2,500m, kick-off con tasa de construccion 6-10 grados/30m, seccion horizontal de 1,500-3,000m dentro del target de Vaca Muerta.")

    pdf.add_page()
    pdf.chapter_title("4", "Procedimiento de Fracking Multietapa")
    pdf.body_text("El fracking multietapa en Vaca Muerta utiliza la tecnologia Plug-and-Perf con intervalos tipicos de 70-100m. Cada etapa requiere 3,000-5,000 m3 de fluido fracturante y 150-300 toneladas de proppant.")
    pdf.body_text("Las presiones de fractura tipicas oscilan entre 600 y 900 bar (8,700-13,000 psi). El diseno de fluido debe optimizarse para minimizar el dano de formacion manteniendo la transportabilidad del proppant.")

    pdf.chapter_subtitle("4.1 Parametros por Etapa")
    widths2 = [45, 45, 35, 35, 30]
    pdf.table_row(["Parametro", "Min", "Nominal", "Max", "Unidad"], widths2, bold=True, fill=True)
    pdf.table_row(["Fluido por etapa", "2,500", "4,000", "6,000", "m3"], widths2)
    pdf.table_row(["Proppant", "100", "220", "350", "ton"], widths2)
    pdf.table_row(["Concentracion proppant", "1.5", "3.0", "5.0", "ppg"], widths2)
    pdf.table_row(["Presion de fractura", "600", "750", "950", "bar"], widths2)
    pdf.table_row(["Tasa de bombeo", "8", "12", "16", "m3/min"], widths2)
    pdf.ln(3)

    pdf.warning_box("Toda operacion de fracking requiere monitoreo sismico continuo. El limite de magnitud inducida es 3.0 Ml.")

    pdf.chapter_title("5", "Control de Pozos")
    pdf.body_text("El control de pozos en Vaca Muerta requiere atencion especial debido a las altas presiones de formacion. El BOP debe ser probado semanalmente a 70% del rated working pressure.")

    pdf.output(os.path.join(OUTPUT_DIR, "MANUAL_PERFORACION_VM_Rev0.pdf"))
    print("Generated: MANUAL_PERFORACION_VM_Rev0.pdf")

    # PDF 2: Normativa IAPG
    pdf = PetroPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(26, 35, 126)
    pdf.cell(0, 20, "NORMATIVA IAPG - RESOLUCIONES SE", align="C", ln=True)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Regulacion Hidrocarburifera Argentina", align="C", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 10, "Rev. 2 | Marzo 2024 | Instituto Argentino del Petroleo y del Gas", align="C", ln=True)
    pdf.ln(15)

    pdf.chapter_title("1", "Resolucion SE 123/2018 - Monitoreo Ambiental")
    pdf.body_text("La Resolucion SE 123/2018 establece que los operadores de areas hidrocarburiferas deben implementar un Plan de Monitoreo Ambiental (PMA) con monitoreo de aguas subterraneas antes, durante y posterior a las operaciones de fracturacion hidraulica.")
    pdf.body_text("Los parametros a monitorear incluyen: BTEX, metales pesados (arsenico, plomo, mercurio), cloruros, pH, conductividad electrica, y metano disuelto. La frecuencia de muestreo es semestral para aguas subterraneas y trimestral para aguas superficiales.")

    pdf.chapter_title("2", "Resolucion SE 144/2014 - Integridad de Pozos")
    pdf.body_text("La Resolucion SE 144/2014 establece los requisitos minimos para la integridad de pozos en operaciones no convencionales. Todo pozo debe contar con cemento de alta calidad que garantice el aislamiento zonal.")
    pdf.body_text("Los requisitos de cementacion incluyen: cobertura del anular del 100% en la zona de interes, resistencia a la compresion minima de 3.45 MPa (500 psi) a 24 horas, y ausencia de canales de migracion detectados por CBL/VDL.")

    pdf.chapter_subtitle("2.1 Tabla de Requisitos de Cementacion")
    widths3 = [60, 40, 40, 50]
    pdf.table_row(["Parametro", "Minimo", "Recomendado", "Metodo de Verificacion"], widths3, bold=True, fill=True)
    pdf.table_row(["Resistencia compresion", "3.45 MPa", ">5.0 MPa", "UCS a 24h"], widths3)
    pdf.table_row(["Espesor anular minimo", "12.7 mm", "19.0 mm", "Ultrasonido"], widths3)
    pdf.table_row(["Cobertura anular", "90%", "100%", "CBL/VDL"], widths3)
    pdf.table_row(["Permeabilidad", "<0.1 mD", "<0.01 mD", "Prueba de presion"], widths3)
    pdf.ln(3)

    pdf.chapter_title("3", "API RP 53 - Sistemas BOP")
    pdf.body_text("La API RP 53 establece los estandares para el diseno, instalacion, operacion y mantenimiento de sistemas de control de pozos (BOP). En Argentina, esta norma es adoptada por referencia en las regulaciones de la Secretaria de Energia.")
    pdf.body_text("Los BOPs utilizados en Vaca Muerta tipicamente tienen rated working pressure de 10,000 o 15,000 psi. El stack minimo recomendado incluye: anular preventer, dos pipe rams, blind-shear ram, y choke & kill lines.")

    pdf.output(os.path.join(OUTPUT_DIR, "NORMATIVA_IAPG_RESOLUCIONES_Rev2.pdf"))
    print("Generated: NORMATIVA_IAPG_RESOLUCIONES_Rev2.pdf")

    # PDF 3: HSE y Seguridad
    pdf = PetroPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(26, 35, 126)
    pdf.cell(0, 20, "MANUAL DE SEGURIDAD Y SALUD OCUPACIONAL", align="C", ln=True)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Operaciones en Campo - Vaca Muerta", align="C", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 10, "Rev. 1 | Enero 2024 | YPF S.A.", align="C", ln=True)
    pdf.ln(15)

    pdf.chapter_title("1", "Identificacion de Peligros")
    pdf.body_text("Las operaciones de perforacion y completacion en Vaca Muerta presentan multiples peligros que deben ser identificados y controlados. Los principales peligros identificados son:")
    pdf.body_text("1. H2S (Sulfuro de Hidrogeno): Concentraciones tipicas en Vaca Muerta varian entre 50 y 500 ppm en el gas de formacion. El H2S es extremadamente toxico (IDLH = 100 ppm) y requiere monitoreo continuo.")
    pdf.body_text("2. Presion de formacion: Las presiones de pore pressure en Vaca Muerta pueden alcanzar 700 bar (10,000 psi), creando riesgo de blowout si no se mantienen los controles adecuados.")
    pdf.body_text("3. Fluidos de perforacion: Los lodos base aceite contienen aromaticos y hidrocarburos que presentan riesgos toxicos y ambientales.")

    pdf.chapter_title("2", "PPE - Equipo de Proteccion Personal")
    pdf.body_text("El siguiente PPE es obligatorio para todas las operaciones de perforacion y completacion:")
    widths4 = [40, 70, 80]
    pdf.table_row(["Area", "PPE Obligatorio", "Especificacion"], widths4, bold=True, fill=True)
    pdf.table_row(["Torre", "Casco, botas, arnes", "Clase E, puntera acero"], widths4)
    pdf.table_row(["Zona H2S", "SCBA, detector", "30 min, alarma 10 ppm"], widths4)
    pdf.table_row(["Quimicos", "Overol, guantes, goggles", "Neopreno, anti-splash"], widths4)
    pdf.table_row(["Ruido", "Protectores auditivos", "NRR >25 dB"], widths4)
    pdf.ln(3)

    pdf.warning_box("La exposicion a H2S por encima de 100 ppm requiere evacuacion inmediata del area. Todo personal debe estar entrenado en el uso de SCBA y conocer las rutas de evacuacion.")

    pdf.chapter_title("3", "Procedimiento de Killing the Well")
    pdf.body_text("El procedimiento de killing the well debe seguirse estrictamente cuando se detecta un kick. Los pasos son:")
    pdf.body_text("Paso 1: Cerrar el BOP (anular o pipe ram segun corresponda).")
    pdf.body_text("Paso 2: Leer SIDPP (shut-in drill pipe pressure) y SICP (shut-in casing pressure).")
    pdf.body_text("Paso 3: Calcular el kill mud weight: KMW = (SIDPP / (0.052 x TVD)) + OMW.")
    pdf.body_text("Paso 4: Preparar el lodo de kill en los tanques de reserva.")
    pdf.body_text("Paso 5: Circular el lodo de kill utilizando el metodo Wait & Weight o Driller's Method.")
    pdf.body_text("Paso 6: Monitorear los retornos y ajustar el choke para mantener la presion de circulacion constante.")
    pdf.body_text("Paso 7: Verificar que SIDPP = 0 y que no hay flujo en el pozo.")

    pdf.output(os.path.join(OUTPUT_DIR, "MANUAL_HSE_SEGURIDAD_VM_Rev1.pdf"))
    print("Generated: MANUAL_HSE_SEGURIDAD_VM_Rev1.pdf")

    # PDF 4: Especificaciones de Equipos
    pdf = PetroPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(26, 35, 126)
    pdf.cell(0, 20, "ESPECIFICACIONES TECNICAS DE EQUIPOS", align="C", ln=True)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "BOPs, Christmas Trees, Bombas y Equipos de Superficie", align="C", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 10, "Rev. 3 | Febrero 2024 | YPF S.A. / TechnipFMC", align="C", ln=True)
    pdf.ln(15)

    pdf.chapter_title("1", "Blowout Preventers (BOP)")
    pdf.body_text("Los BOPs utilizados en Vaca Muerta deben cumplir con API 16A y API 16D. Las especificaciones tipicas son:")
    widths5 = [50, 35, 35, 35, 35]
    pdf.table_row(["Componente", "RWP (psi)", "Diametro", "Cierre (s)", "Prueba"], widths5, bold=True, fill=True)
    pdf.table_row(["Anular preventer", "10,000", "18 3/4\"", "<30", "Semanal"], widths5)
    pdf.table_row(["Pipe ram", "15,000", "18 3/4\"", "<15", "Semanal"], widths5)
    pdf.table_row(["Blind-shear ram", "15,000", "18 3/4\"", "<15", "Post-reparacion"], widths5)
    pdf.table_row(["Choke line", "10,000", "4\"", "N/A", "Mensual"], widths5)
    pdf.ln(3)

    pdf.chapter_title("2", "Christmas Trees")
    pdf.body_text("Los Christmas Trees para pozos no convencionales en Vaca Muerta tipicamente son de tipo monoblock con las siguientes caracteristicas:")
    pdf.body_text("- Rated Working Pressure: 10,000 psi (69 MPa)")
    pdf.body_text("- Material: ASTM A182 F22 Clase 3 (cromo-molibdeno) para resistencia a H2S")
    pdf.body_text("- Conexiones: API 6A BX-155 o RX-54")
    pdf.body_text("- Valvulas maestras: 2 valvulas de compuerta API 6A clase EE")
    pdf.body_text("- Swab valve: 1 valvula de compuerta para trabajo de cable")
    pdf.body_text("- Medidores de presion: Transmisores Rosemount 3051S con rango 0-10,000 psi")

    pdf.chapter_title("3", "Bombas de Lodo")
    pdf.body_text("Las bombas de lodo para perforacion en Vaca Muerta tipicamente son triplex de alta presion:")
    widths6 = [45, 40, 35, 35, 35]
    pdf.table_row(["Modelo", "HP", "Presion max", "Caudal max", "Fabricante"], widths6, bold=True, fill=True)
    pdf.table_row(["W-2200", "2,200", "7,500 psi", "1,200 gpm", "Weatherford"], widths6)
    pdf.table_row(["T-1600", "1,600", "5,000 psi", "900 gpm", "NOV"], widths6)
    pdf.table_row(["P-11", "1,100", "3,500 psi", "750 gpm", "Gardner Denver"], widths6)
    pdf.ln(3)

    pdf.output(os.path.join(OUTPUT_DIR, "ESPECIFICACIONES_EQUIPOS_VM_Rev3.pdf"))
    print("Generated: ESPECIFICACIONES_EQUIPOS_VM_Rev3.pdf")

    # PDF 5: Reporte de Pozo
    pdf = PetroPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(26, 35, 126)
    pdf.cell(0, 20, "REPORTE DE POZO - LOMA CAMPANA 1234", align="C", ln=True)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Pozo Horizontal - Formacion Vaca Muerta", align="C", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 10, "Rev. 0 | Mayo 2024 | YPF S.A.", align="C", ln=True)
    pdf.ln(15)

    pdf.chapter_title("1", "Datos Generales del Pozo")
    pdf.body_text("Nombre del pozo: Loma Campana 1234")
    pdf.body_text("Ubicacion: Sector Norte, Yacimiento Loma Campana, Cuenca Neuquina")
    pdf.body_text("Coordenadas: 38°15'22\"S, 68°45'15\"W")
    pdf.body_text("Profundidad total medida (TMD): 5,847 m")
    pdf.body_text("Profundidad total vertical (TVD): 2,734 m")
    pdf.body_text("Longitud horizontal: 2,100 m")
    pdf.body_text("Objetivo: Formacion Vaca Muerta (Miembro Inferior)")

    pdf.chapter_title("2", "Resultados de Perforacion")
    pdf.body_text("La perforacion se realizo con una sarta de 8 1/2\" utilizando lodo base aceite sintetico de 1.85 g/cm3. El ROP promedio en la seccion horizontal fue de 12.5 m/h.")
    pdf.body_text("Se registraron los siguientes parametros de formacion:")
    widths7 = [50, 40, 40, 30, 30]
    pdf.table_row(["Parametro", "Valor", "Unidad", "Metodo", "Profundidad"], widths7, bold=True, fill=True)
    pdf.table_row(["Porosidad", "8.5", "%", "NMR", "2,650 m"], widths7)
    pdf.table_row(["Permeabilidad", "0.0015", "mD", "Core", "2,650 m"], widths7)
    pdf.table_row(["Presion de poros", "470", "bar", "RFT", "2,650 m"], widths7)
    pdf.table_row(["Temperatura", "125", "°C", "DTS", "2,650 m"], widths7)
    pdf.table_row(["TOC", "5.2", "%", "Pyrolisis", "2,650 m"], widths7)
    pdf.ln(3)

    pdf.chapter_title("3", "Resultados de Fracking")
    pdf.body_text("Se completaron 35 etapas de fracking con tecnologia Plug-and-Perf. Los resultados por etapa se resumen a continuacion:")
    pdf.body_text("Etapa promedio: 4,200 m3 de fluido, 230 ton de proppant, presion maxima 820 bar.")
    pdf.body_text("El indice de productividad inicial (IP) fue de 450 bbl/d/psi, con una declinacion del 65% en el primer ano.")

    pdf.output(os.path.join(OUTPUT_DIR, "REPORTE_POZO_LOMA_CAMPANA_1234.pdf"))
    print("Generated: REPORTE_POZO_LOMA_CAMPANA_1234.pdf")

    # PDF 6: Fluidos de Perforacion
    pdf = PetroPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(26, 35, 126)
    pdf.cell(0, 20, "MANUAL DE FLUIDOS DE PERFORACION", align="C", ln=True)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Diseno, Mantenimiento y Control de Lodos", align="C", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 10, "Rev. 1 | Junio 2024 | YPF S.A.", align="C", ln=True)
    pdf.ln(15)

    pdf.chapter_title("1", "Tipos de Fluidos")
    pdf.body_text("En Vaca Muerta se utilizan principalmente tres tipos de fluidos de perforacion:")
    pdf.body_text("1. Lodo base aceite sintetico (SBM): Densidad 1.60-2.20 g/cm3, usado en secciones profundas y horizontales.")
    pdf.body_text("2. Lodo base agua (WBM): Densidad 1.05-1.80 g/cm3, usado en secciones superficiales.")
    pdf.body_text("3. Lodo de baja invasion (LWD): Diseñado para minimizar el dano a la formacion.")

    pdf.chapter_title("2", "Parametros de Control")
    widths8 = [45, 35, 35, 35, 40]
    pdf.table_row(["Parametro", "WBM", "SBM", "Unidad", "Frecuencia"], widths8, bold=True, fill=True)
    pdf.table_row(["Densidad", "1.05-1.80", "1.60-2.20", "g/cm3", "Cada turno"], widths8)
    pdf.table_row(["Viscosidad PV", "15-35", "35-65", "cP", "Cada turno"], widths8)
    pdf.table_row(["Viscosidad YP", "8-15", "12-20", "lb/100ft2", "Cada turno"], widths8)
    pdf.table_row(["Gel 10s", "8-12", "15-25", "lb/100ft2", "Cada turno"], widths8)
    pdf.table_row(["Solidos", "<6", "<8", "%", "Diario"], widths8)
    pdf.ln(3)

    pdf.chapter_title("3", "Tratamiento de Lodo")
    pdf.body_text("El tratamiento del lodo base aceite incluye:")
    pdf.body_text("- Dilucion continua: 5-10% del volumen activo por dia")
    pdf.body_text("- Centrifugacion: Remover solidos de perforacion >5 micrones")
    pdf.body_text("- Ajuste de emulsion: Mantener la relacion aceite/agua entre 80/20 y 90/10")
    pdf.body_text("- Control de baritas: D10 > 2 micrones, D50 entre 15-25 micrones")

    pdf.output(os.path.join(OUTPUT_DIR, "MANUAL_FLUIDOS_PERFORACION_Rev1.pdf"))
    print("Generated: MANUAL_FLUIDOS_PERFORACION_Rev1.pdf")

    # PDF 7: Cementacion
    pdf = PetroPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(26, 35, 126)
    pdf.cell(0, 20, "MANUAL DE CEMENTACION DE POZOS", align="C", ln=True)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Diseno, Ejecucion y Evaluacion", align="C", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 10, "Rev. 2 | Julio 2024 | YPF S.A.", align="C", ln=True)
    pdf.ln(15)

    pdf.chapter_title("1", "Diseno de Cemento")
    pdf.body_text("El diseno del sistema de cementacion debe considerar:")
    pdf.body_text("- Presion de formacion y gradiente de fractura")
    pdf.body_text("- Temperatura de fondo de pozo (BHST)")
    pdf.body_text("- Presencia de H2S y CO2")
    pdf.body_text("- Geometria del pozo (inclinacion, desviacion)")

    pdf.chapter_title("2", "Sistemas de Cemento")
    widths9 = [40, 45, 45, 30, 30]
    pdf.table_row(["Tipo", "Densidad", "Resistencia", "Aplicacion", "Aditivos"], widths9, bold=True, fill=True)
    pdf.table_row(["Lead", "1.60-1.70", "10 MPa/24h", "Anular superior", "Extensor"], widths9)
    pdf.table_row(["Tail", "1.85-1.95", "20 MPa/24h", "Anular productor", "Silica, anti-gas"], widths9)
    pdf.table_row(["Flexible", "1.70-1.80", "15 MPa/24h", "Zona de cizalla", "Elastomer"], widths9)
    pdf.table_row(["Ligero", "1.30-1.50", "8 MPa/24h", "Perdida de circulacion", "Espumante"], widths9)
    pdf.ln(3)

    pdf.chapter_title("3", "Evaluacion de Cemento")
    pdf.body_text("La evaluacion de la calidad del cemento se realiza con:")
    pdf.body_text("1. CBL/VDL (Cement Bond Log): Evalua la union cemento-casing y cemento-formacion.")
    pdf.body_text("2. USIT (Ultrasonic Imaging Tool): Proporciona imagen 360° del anular.")
    pdf.body_text("3. RBT (Radial Bond Tool): Mide la resistencia radial del cemento.")
    pdf.body_text("Criterios de aceptacion: Amplitud CBL < 20% en zona de interes, VDL con patron de forma.")

    pdf.output(os.path.join(OUTPUT_DIR, "MANUAL_CEMENTACION_POZOS_Rev2.pdf"))
    print("Generated: MANUAL_CEMENTACION_POZOS_Rev2.pdf")

    # PDF 8: Geomecanica
    pdf = PetroPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(26, 35, 126)
    pdf.cell(0, 20, "ESTUDIO GEOMECANICO - VACA MUERTA", align="C", ln=True)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Modelo de Esfuerzos y Propiedades Mecanicas", align="C", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 10, "Rev. 0 | Agosto 2024 | YPF S.A. / Schlumberger", align="C", ln=True)
    pdf.ln(15)

    pdf.chapter_title("1", "Modelo de Esfuerzos In-Situ")
    pdf.body_text("El modelo de esfuerzos in-situ para Vaca Muerta se basa en datos de minifracs, LOTs, y analisis de registros sonic.")
    pdf.body_text("Gradientes de esfuerzo tipicos:")
    widths10 = [50, 40, 40, 30, 30]
    pdf.table_row(["Esfuerzo", "Gradiente", "Unidad", "Profundidad", "Metodo"], widths10, bold=True, fill=True)
    pdf.table_row(["Vertical (Sv)", "0.022-0.024", "MPa/m", "2,500 m", "Densidad"], widths10)
    pdf.table_row(["Min horizontal (Shmin)", "0.018-0.020", "MPa/m", "2,500 m", "Minifrac"], widths10)
    pdf.table_row(["Max horizontal (SHmax)", "0.024-0.027", "MPa/m", "2,500 m", "LOT"], widths10)
    pdf.table_row(["Pore pressure", "0.015-0.017", "MPa/m", "2,500 m", "RFT/DST"], widths10)
    pdf.ln(3)

    pdf.chapter_title("2", "Propiedades Mecanicas")
    pdf.body_text("Las propiedades mecanicas de Vaca Muerta varian segun la litologia:")
    pdf.body_text("Lodolitas: Young 15-25 GPa, Poisson 0.25-0.30, UCS 40-80 MPa")
    pdf.body_text("Areniscas: Young 30-50 GPa, Poisson 0.20-0.25, UCS 80-150 MPa")
    pdf.body_text("Calizas: Young 50-70 GPa, Poisson 0.20-0.25, UCS 100-200 MPa")

    pdf.chapter_title("3", "Ventana de Densidad de Lodo")
    pdf.body_text("La ventana de densidad de lodo para perforar Vaca Muerta horizontalmente es estrecha:")
    pdf.body_text("Densidad minima: 1.70 g/cm3 (para evitar colapso en Shmin)")
    pdf.body_text("Densidad maxima: 1.95 g/cm3 (para evitar fracturar la formacion)")
    pdf.body_text("Margen operativo: 0.25 g/cm3")
    pdf.body_text("Estrechamiento en zonas de falla o fracturas naturales.")

    pdf.output(os.path.join(OUTPUT_DIR, "ESTUDIO_GEOMECANICO_VM_Rev0.pdf"))
    print("Generated: ESTUDIO_GEOMECANICO_VM_Rev0.pdf")

    print("\n" + "="*60)
    print("All 8 PDFs generated successfully!")
    print(f"Location: {OUTPUT_DIR}")
    print("="*60)


if __name__ == "__main__":
    generate_all_pdfs()
