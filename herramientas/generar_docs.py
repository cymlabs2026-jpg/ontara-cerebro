"""Genera los documentos de la empresa ficticia para la demo pública de Ontara Cerebro."""
import csv
import os
import random

import docx
import openpyxl
import pptx
from openpyxl.styles import Font, PatternFill
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demo_docs")
EMP = "Comercializadora El Samán S.A.S."
NOTA = "Empresa ficticia creada por C&M Labs para la demostración de Ontara Cerebro. Datos inventados."
random.seed(7)


def carpeta(nombre):
    ruta = os.path.join(OUT, nombre)
    os.makedirs(ruta, exist_ok=True)
    return ruta


def documento(ruta, titulo, bloques):
    d = docx.Document()
    d.add_heading(titulo, 0)
    d.add_paragraph(f"{EMP} · {NOTA}").italic = True
    for b in bloques:
        if isinstance(b, tuple) and b[0] == "h":
            d.add_heading(b[1], 1)
        elif isinstance(b, tuple) and b[0] == "lista":
            for item in b[1]:
                d.add_paragraph(item, style="List Number" if b[2] else "List Bullet")
        elif isinstance(b, tuple) and b[0] == "tabla":
            filas = b[1]
            t = d.add_table(rows=len(filas), cols=len(filas[0]))
            t.style = "Light Grid Accent 1"
            for i, fila in enumerate(filas):
                for j, v in enumerate(fila):
                    t.cell(i, j).text = str(v)
        else:
            d.add_paragraph(b)
    d.save(ruta)


def pdf(ruta, titulo, bloques):
    est = getSampleStyleSheet()
    hist = [Paragraph(titulo, est["Title"]), Paragraph(f"<i>{EMP} · {NOTA}</i>", est["Normal"]), Spacer(1, 12)]
    for b in bloques:
        if isinstance(b, tuple) and b[0] == "h":
            hist += [Spacer(1, 8), Paragraph(b[1], est["Heading2"])]
        elif isinstance(b, tuple) and b[0] == "tabla":
            hist.append(Table(b[1]))
        else:
            hist.append(Paragraph(b, est["BodyText"]))
    SimpleDocTemplate(ruta, pagesize=letter).build(hist)


def libro(ruta, hojas):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for nombre, filas in hojas:
        ws = wb.create_sheet(nombre)
        for fila in filas:
            ws.append(fila)
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="0B3B4F")
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = max(12, min(40, max(len(str(c.value or "")) for c in col) + 2))
    wb.save(ruta)


# ------------------------------------------------------------------ 1. Operaciones de bodega
op = carpeta("01_Operaciones_Bodega")
documento(os.path.join(op, "Manual_Recepcion_de_Mercancia.docx"), "Manual de recepción de mercancía", [
    "Código: OP-MAN-01 · Versión 3 · Vigente desde el 1 de marzo de 2026 · Responsable: Jefe de Bodega Palmira, Andrés Quintero.",
    ("h", "1. Horario y agendamiento"),
    "La bodega de Palmira recibe mercancía de lunes a sábado de 6:00 a. m. a 2:00 p. m. Todo proveedor debe agendar su cita con al menos 24 horas de anticipación en el portal de citas o al correo recepcion@elsaman-demo.co. Vehículos sin cita se atienden solo si hay muelle libre y después de las 12:00 m.",
    ("h", "2. Documentos obligatorios"),
    ("lista", ["Orden de compra aprobada en el sistema (número OC).", "Factura electrónica o remisión del proveedor.",
               "Lista de empaque con lotes y fechas de vencimiento.", "Certificado de calidad para alimentos y químicos."], False),
    ("h", "3. Pasos de la recepción"),
    ("lista", ["Verificar la cita y asignar muelle.", "Inspeccionar el vehículo: limpieza, temperatura (máximo 8 °C para refrigerados) y sellos.",
               "Contar y pesar: la tolerancia permitida es ±2 % del peso declarado; por encima se reporta novedad.",
               "Revisar fechas de vencimiento: no se recibe producto con menos del 60 % de vida útil restante.",
               "Registrar la entrada en el WMS y rotular cada estiba con su código LPN.",
               "Ubicar la mercancía según la regla de slotting (ver Manual de Slotting) en máximo 4 horas."], True),
    ("h", "4. Novedades"),
    "Faltantes, sobrantes, averías o producto vencido se registran en el formato OP-FOR-07 con foto y firma del conductor. El área de Compras debe resolver la novedad con el proveedor en un plazo máximo de 3 días hábiles.",
    ("h", "5. Indicadores"),
    ("tabla", [["Indicador", "Meta"], ["Tiempo promedio de descargue", "≤ 45 minutos por vehículo"],
               ["Recepciones con novedad", "≤ 3 %"], ["Mercancía ubicada en 4 horas", "≥ 98 %"]]),
])

pdf(os.path.join(op, "Reglamento_Seguridad_Montacargas.pdf"), "Reglamento de seguridad para montacargas", [
    "Código: SST-REG-03 · Aprobado por el Comité de Seguridad y Salud en el Trabajo (COPASST) en enero de 2026.",
    ("h", "1. Quién puede operar"),
    "Solo operadores con licencia interna vigente. La licencia exige curso teórico-práctico de 16 horas, examen médico ocupacional y recertificación anual. A la fecha la bodega tiene 9 operadores certificados.",
    ("h", "2. Reglas de operación"),
    "Velocidad máxima de 8 km/h en pasillos y 5 km/h en zonas de picking y muelles. Uso obligatorio de cinturón, casco y chaleco reflectivo. Prohibido transportar personas o levantar cargas por encima de la capacidad de placa (2,5 toneladas en los equipos de la bodega). La horquilla debe ir a 15 cm del piso al desplazarse.",
    ("h", "3. Inspección preoperacional"),
    "Antes de cada turno el operador diligencia la lista de chequeo SST-FOR-11: frenos, bocina, luces, nivel de batería o gas, horquillas, mástil y cadenas. Un equipo con falla se bloquea con tarjeta roja y se reporta a mantenimiento.",
    ("h", "4. Sanciones"),
    "Primera falta: llamado de atención escrito. Segunda falta: suspensión de la licencia por 30 días y reentrenamiento. Falta grave (transportar personas, operar bajo efectos de alcohol): retiro definitivo de la licencia.",
    ("h", "5. Accidentalidad"),
    "En 2025 se registraron 4 incidentes con montacargas, 1 con incapacidad. La meta 2026 es cero accidentes con incapacidad.",
])

pdf(os.path.join(op, "Manual_de_Slotting.pdf"), "Manual de slotting (ubicación de productos)", [
    "Código: OP-MAN-04 · Versión 1 · Septiembre de 2026.",
    ("h", "1. Qué es el slotting"),
    "El slotting es la asignación de cada producto (SKU) a la ubicación más conveniente de la bodega según su rotación, peso y volumen. Un buen slotting reduce los recorridos de picking y el costo por pedido.",
    ("h", "2. Clasificación ABC"),
    "Clase A: el 20 % de los SKU que generan cerca del 80 % de los movimientos. Van en la Zona Dorada (niveles 1 y 2, cerca de los muelles de despacho). Clase B: rotación media, pasillos intermedios. Clase C: baja rotación, niveles altos y fondo de la bodega.",
    ("h", "3. Reglas"),
    "Productos pesados (más de 20 kg) siempre en nivel 1. Químicos separados de alimentos con al menos un pasillo de distancia. La clasificación ABC se recalcula cada trimestre con los datos del WMS.",
    ("h", "4. Resultados esperados"),
    "Con el reslotting de octubre de 2026 se espera reducir el recorrido promedio de picking de 1,8 km a 1,2 km por turno y subir la productividad de 95 a 120 líneas por hora.",
])

inv = [["SKU", "Descripción", "Categoría", "Clase ABC", "Ubicación", "Stock (und)", "Stock mínimo", "Costo unitario (COP)", "Rotación mensual (und)"]]
productos = [("Arroz premium 5 kg", "Abarrotes"), ("Aceite vegetal 3 L", "Abarrotes"), ("Azúcar blanca 2,5 kg", "Abarrotes"),
             ("Café molido 500 g", "Abarrotes"), ("Panela pulverizada 1 kg", "Abarrotes"), ("Atún en agua 170 g", "Enlatados"),
             ("Leche UHT 1 L x6", "Lácteos"), ("Queso campesino 1 kg", "Refrigerados"), ("Yogur fresa 1 L", "Refrigerados"),
             ("Detergente en polvo 3 kg", "Aseo"), ("Jabón de loza 1 kg", "Aseo"), ("Papel higiénico x12", "Aseo"),
             ("Cloro 3,8 L", "Químicos"), ("Desinfectante 2 L", "Químicos"), ("Gaseosa cola 1,5 L x6", "Bebidas"),
             ("Agua sin gas 600 ml x24", "Bebidas"), ("Jugo de mango 1 L", "Bebidas"), ("Galletas de soda x9", "Snacks"),
             ("Papas fritas 150 g", "Snacks"), ("Chocolate de mesa 500 g", "Abarrotes"), ("Lentejas 500 g", "Granos"),
             ("Fríjol cargamanto 500 g", "Granos"), ("Pasta spaghetti 1 kg", "Abarrotes"), ("Harina de maíz 1 kg", "Abarrotes"),
             ("Salsa de tomate 400 g", "Abarrotes"), ("Pañales etapa 3 x30", "Cuidado personal"), ("Shampoo 750 ml", "Cuidado personal"),
             ("Crema dental 3x75 ml", "Cuidado personal"), ("Bolsas de basura x10", "Aseo"), ("Servilletas x300", "Aseo")]
for i, (desc, cat) in enumerate(productos, 1):
    clase = "A" if i <= 8 else ("B" if i <= 18 else "C")
    rot = random.randint(900, 2500) if clase == "A" else (random.randint(300, 900) if clase == "B" else random.randint(40, 300))
    minimo = int(rot * 0.5)
    stock = int(rot * random.uniform(0.25, 1.6))
    pasillo = "P01" if clase == "A" else ("P04" if clase == "B" else "P08")
    inv.append([f"SAM-{1000 + i}", desc, cat, clase, f"{pasillo}-N{1 if clase == 'A' else random.randint(2, 4)}-{i:02d}",
                stock, minimo, random.randint(3, 60) * 500, rot])
bajo = [["SKU", "Descripción", "Stock (und)", "Stock mínimo", "Faltante para mínimo"]]
for f in inv[1:]:
    if f[5] < f[6]:
        bajo.append([f[0], f[1], f[5], f[6], f[6] - f[5]])
libro(os.path.join(op, "Inventario_Bodega_Palmira_2026-10-31.xlsx"), [("Inventario", inv), ("Bajo mínimo", bajo)])

# ------------------------------------------------------------------ 2. Indicadores y comités
ind = carpeta("02_Indicadores_y_Comites")
meses = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10"]
otif = [88.4, 89.1, 90.3, 89.7, 91.2, 92.0, 91.5, 92.8, 93.4, 94.1]
exactitud = [96.2, 96.5, 97.0, 96.8, 97.4, 97.9, 98.1, 98.0, 98.3, 98.6]
costo = [6850, 6790, 6720, 6810, 6640, 6580, 6600, 6490, 6420, 6350]
with open(os.path.join(ind, "KPIs_Logistica_2026.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["mes", "otif_pct", "exactitud_inventario_pct", "costo_por_pedido_cop", "pedidos_despachados", "devoluciones_pct", "lineas_por_hora"])
    for i, m in enumerate(meses):
        w.writerow([m, otif[i], exactitud[i], costo[i], 4200 + i * 130 + random.randint(-80, 80),
                    round(random.uniform(1.4, 2.6), 1), 92 + i * 2 + random.randint(-2, 2)])

documento(os.path.join(ind, "Acta_Comite_Operaciones_2026-10-28.docx"), "Acta del Comité de Operaciones · 28 de octubre de 2026", [
    "Asistentes: Laura Restrepo (Gerente General), Andrés Quintero (Jefe de Bodega), Camila Ortiz (Coordinadora de Transporte), Felipe Mora (Analista de Inventarios), Diana Cárdenas (Cartera).",
    ("h", "1. Resultados de septiembre y octubre"),
    "El OTIF subió de 93,4 % en septiembre a 94,1 % en octubre, todavía por debajo de la meta anual de 95 %. La exactitud de inventario llegó a 98,6 %, su mejor nivel del año. El costo por pedido bajó a 6.350 pesos.",
    ("h", "2. Decisiones"),
    ("lista", ["Abrir un turno nocturno de picking (10:00 p. m. a 6:00 a. m.) desde el 18 de noviembre de 2026 para atender la temporada de diciembre. Responsable: Andrés Quintero.",
               "Contratar 6 auxiliares temporales para noviembre y diciembre. Responsable: Gestión Humana.",
               "Implementar la ruta Palmira–Buga–Tuluá los martes y viernes para bajar los retrasos del norte del Valle. Responsable: Camila Ortiz.",
               "Llamar uno a uno a los 5 clientes con cartera vencida a más de 60 días antes del 15 de noviembre. Responsable: Diana Cárdenas."], True),
    ("h", "3. Riesgos"),
    "Productos bajo stock mínimo en categorías de clase A (abarrotes y lácteos) podrían afectar el OTIF de diciembre. Se pide a Compras adelantar pedidos en la semana 46.",
    ("h", "4. Próximo comité"),
    "25 de noviembre de 2026, 7:00 a. m., sala de juntas de la bodega Palmira.",
])

cartera = [["Cliente", "Ciudad", "Factura", "Valor (COP)", "Fecha vencimiento", "Días de mora", "Estado"]]
clientes = [("Supermercado La Ceiba", "Cali"), ("Minimercado Doña Rosa", "Palmira"), ("Tienda El Progreso", "Buga"),
            ("Autoservicio Los Andes", "Tuluá"), ("Droguería y Más", "Cali"), ("Market Express Yumbo", "Yumbo"),
            ("Surtitodo Candelaria", "Candelaria"), ("Fruver La Cosecha", "Palmira"), ("Granero San José", "Florida"),
            ("Distribuciones Pradera", "Pradera")]
mora = [95, 72, 64, 61, 48, 33, 21, 12, 5, 0]
for i, ((c, ciudad), d) in enumerate(zip(clientes, mora)):
    estado = "Crítico" if d > 60 else ("En gestión" if d > 30 else ("Al día" if d == 0 else "Seguimiento"))
    cartera.append([c, ciudad, f"FE-{8800 + i}", random.randint(4, 48) * 250000, f"2026-{9 if d > 40 else 10}-{random.randint(1, 28):02d}", d, estado])
libro(os.path.join(ind, "Cartera_Vencida_2026-10-31.xlsx"), [("Cartera", cartera)])

# ------------------------------------------------------------------ 3. Comercial y clientes
com = carpeta("03_Comercial_y_Clientes")
pdf(os.path.join(com, "Politica_de_Devoluciones.pdf"), "Política de devoluciones para clientes", [
    "Código: COM-POL-02 · Vigente desde el 1 de enero de 2026.",
    ("h", "1. Plazos"),
    "El cliente puede solicitar la devolución dentro de los 30 días calendario siguientes a la entrega. Producto refrigerado: máximo 48 horas después de la entrega.",
    ("h", "2. Causales aceptadas"),
    "Producto averiado en el transporte, vencido o con menos del 30 % de vida útil al momento de la entrega, referencia equivocada, o cantidades diferentes a la factura.",
    ("h", "3. Causales no aceptadas"),
    "Producto en buen estado que el cliente no logró vender, mercancía sin empaque original o productos de temporada después de la fecha de la promoción.",
    ("h", "4. Procedimiento"),
    "El cliente reporta por WhatsApp (+57 300 000 0000, línea de demostración) o en el portal con número de factura y fotos. El conductor recoge el producto en la siguiente visita de la ruta. La nota crédito se emite en máximo 5 días hábiles después de recibir el producto en bodega.",
    ("h", "5. Meta"),
    "Mantener las devoluciones por debajo del 2 % de los pedidos despachados.",
])

p = pptx.Presentation()
diapositivas = [
    ("Comercializadora El Samán S.A.S.", NOTA),
    ("Quiénes somos", "Distribuidor mayorista de consumo masivo con bodega en Palmira (Valle del Cauca).\nFundada en 2014 · 85 empleados · 1.200 clientes activos."),
    ("Cobertura", "Palmira, Cali, Yumbo, Candelaria, Pradera, Florida, Buga y Tuluá.\nEntregas en 24 horas en el área metropolitana de Cali y 48 horas en el norte del Valle."),
    ("Portafolio", "Más de 1.800 referencias: abarrotes, granos, lácteos y refrigerados, bebidas, aseo, químicos y cuidado personal."),
    ("Servicios", "Venta mayorista · Almacenamiento para terceros · Distribución de última milla · Reabastecimiento automático para tiendas."),
    ("Indicadores 2026", "OTIF de octubre: 94,1 % · Exactitud de inventario: 98,6 % · Devoluciones menores al 2 %."),
    ("Contacto", "comercial@elsaman-demo.co · Bodega: Zona Franca del Pacífico (dirección de demostración)."),
]
for titulo, texto in diapositivas:
    s = p.slides.add_slide(p.slide_layouts[1])
    s.shapes.title.text = titulo
    s.placeholders[1].text = texto
p.save(os.path.join(com, "Presentacion_Comercial_2026.pptx"))

with open(os.path.join(com, "Preguntas_Frecuentes_Clientes.md"), "w", encoding="utf-8") as f:
    f.write(f"""# Preguntas frecuentes de clientes
*{EMP} · {NOTA}*

**¿Cuál es el pedido mínimo?** 600.000 pesos antes de IVA para Cali y Palmira; 900.000 pesos para Buga y Tuluá.

**¿Cuándo llega mi pedido?** Pedidos confirmados antes de las 3:00 p. m. se entregan al día siguiente en el área metropolitana de Cali y Palmira, y en 48 horas en el norte del Valle.

**¿Qué medios de pago aceptan?** Transferencia, PSE y crédito a 30 días para clientes con más de 6 meses de compras y buen historial.

**¿Cómo hago una devolución?** Ver la Política de Devoluciones COM-POL-02: plazo de 30 días (48 horas para refrigerados) y nota crédito en 5 días hábiles.

**¿Tienen precios por volumen?** Sí: 3 % de descuento por pedidos superiores a 3 millones de pesos y 5 % por encima de 6 millones.
""")

# ------------------------------------------------------------------ 4. Talento humano
th = carpeta("04_Talento_Humano")
plan = [["Curso", "Dirigido a", "Fecha", "Horas", "Responsable", "Estado"],
        ["Operación segura de montacargas (recertificación)", "Operadores de montacargas", "2026-02-14", 16, "SST", "Ejecutado"],
        ["Buenas prácticas de almacenamiento de alimentos", "Auxiliares de bodega", "2026-03-21", 8, "Calidad", "Ejecutado"],
        ["Uso del WMS: recepción y ubicación", "Auxiliares de recepción", "2026-05-09", 6, "Jefe de Bodega", "Ejecutado"],
        ["Servicio al cliente en la entrega", "Conductores", "2026-07-11", 4, "Comercial", "Ejecutado"],
        ["Slotting y clasificación ABC", "Supervisores", "2026-09-19", 6, "Jefe de Bodega", "Ejecutado"],
        ["Inducción temporada de diciembre", "Auxiliares temporales", "2026-11-14", 8, "Gestión Humana", "Programado"],
        ["Primeros auxilios y brigada de emergencias", "Brigadistas", "2026-11-28", 12, "SST", "Programado"],
        ["Excel y Power BI para indicadores", "Analistas y coordinadores", "2026-12-05", 10, "C&M Labs (proveedor)", "Programado"]]
libro(os.path.join(th, "Plan_de_Capacitacion_2026.xlsx"), [("Plan 2026", plan)])

documento(os.path.join(th, "Reglamento_Turnos_y_Horarios.docx"), "Reglamento de turnos y horarios de bodega", [
    ("h", "Turnos vigentes"),
    ("tabla", [["Turno", "Horario", "Personal"], ["Mañana", "6:00 a. m. – 2:00 p. m.", "Recepción, ubicación y picking"],
               ["Tarde", "2:00 p. m. – 10:00 p. m.", "Picking, alistamiento y despacho"],
               ["Noche (temporada)", "10:00 p. m. – 6:00 a. m.", "Picking de pedidos del día siguiente; desde el 18 de noviembre de 2026"]]),
    "Los recargos nocturnos y dominicales se liquidan según la ley colombiana vigente. Los cambios de turno se solicitan al supervisor con 48 horas de anticipación.",
    "El tiempo de almuerzo es de 45 minutos y hay dos pausas activas de 10 minutos por turno.",
])
print("Documentos creados en", OUT)
for r, _, fs in os.walk(OUT):
    for f in sorted(fs):
        print(" ", os.path.relpath(os.path.join(r, f), OUT))
