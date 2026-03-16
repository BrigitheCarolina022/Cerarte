from flask import Flask, render_template, request, jsonify, redirect, url_for, make_response
import sqlite3, os
from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), 'ceramicas.db')

# ── Paleta de colores ámbar (igual que la web) ──────────────
AMBER_DARK  = colors.HexColor('#78350f')   # títulos principales
AMBER       = colors.HexColor('#92400e')   # cabeceras tabla / bordes
AMBER_MED   = colors.HexColor('#d97706')   # acento total a pagar
AMBER_LITE  = colors.HexColor('#fef3c7')   # fondo filas alternas / info
AMBER_THEAD = colors.HexColor('#92400e')   # fondo header tabla
ORANGE_BG   = colors.HexColor('#fff7ed')   # fondo general suave
WHITE       = colors.white
GRAY_TXT    = colors.HexColor('#374151')
GRAY_LIGHT  = colors.HexColor('#f3f4f6')
GRAY_BORDER = colors.HexColor('#d1d5db')
GREEN_DISC  = colors.HexColor('#15803d')

# ── Helpers ─────────────────────────────────────────────────
def P(text, style): return Paragraph(str(text), style)

def generar_pdf_factura(factura, items):
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        rightMargin=2.2*cm, leftMargin=2.2*cm,
        topMargin=2*cm,     bottomMargin=2*cm
    )

    # ── Estilos ─────────────────────────────────────────────
    BASE = getSampleStyleSheet()['Normal']

    def S(name, **kw):
        return ParagraphStyle(name, parent=BASE, **kw)

    titulo_s  = S('tit',  fontSize=26, textColor=AMBER_DARK, fontName='Helvetica-Bold',
                  alignment=TA_CENTER, spaceAfter=0)
    sub_s     = S('sub',  fontSize=10, textColor=AMBER,      fontName='Helvetica',
                  alignment=TA_CENTER, spaceAfter=0)

    lbl_s     = S('lbl',  fontSize=10, textColor=WHITE,       fontName='Helvetica-Bold')
    val_s     = S('val',  fontSize=10, textColor=GRAY_TXT,    fontName='Helvetica')

    hdr_l_s   = S('hl',   fontSize=10, textColor=WHITE,       fontName='Helvetica-Bold', alignment=TA_LEFT)
    hdr_c_s   = S('hc',   fontSize=10, textColor=WHITE,       fontName='Helvetica-Bold', alignment=TA_CENTER)
    hdr_r_s   = S('hr',   fontSize=10, textColor=WHITE,       fontName='Helvetica-Bold', alignment=TA_RIGHT)

    cel_l_s   = S('cl',   fontSize=10, textColor=GRAY_TXT,    fontName='Helvetica',      alignment=TA_LEFT)
    cel_c_s   = S('cc',   fontSize=10, textColor=GRAY_TXT,    fontName='Helvetica',      alignment=TA_CENTER)
    cel_r_s   = S('cr',   fontSize=10, textColor=GRAY_TXT,    fontName='Helvetica',      alignment=TA_RIGHT)
    cel_rb_s  = S('crb',  fontSize=10, textColor=GRAY_TXT,    fontName='Helvetica-Bold', alignment=TA_RIGHT)

    tot_lbl_s = S('tl',   fontSize=10, textColor=GRAY_TXT,    fontName='Helvetica-Bold', alignment=TA_RIGHT)
    tot_val_s = S('tv',   fontSize=10, textColor=GRAY_TXT,    fontName='Helvetica-Bold', alignment=TA_RIGHT)
    disc_s    = S('ds',   fontSize=10, textColor=GREEN_DISC,  fontName='Helvetica-Bold', alignment=TA_RIGHT)
    total_lbl = S('TL',   fontSize=14, textColor=AMBER_DARK,  fontName='Helvetica-Bold', alignment=TA_RIGHT)
    total_val = S('TV',   fontSize=14, textColor=AMBER_MED,   fontName='Helvetica-Bold', alignment=TA_RIGHT)

    foot_s    = S('ft',   fontSize=8,  textColor=AMBER,       fontName='Helvetica',      alignment=TA_CENTER)

    story = []
    W = 17.6 * cm   # ancho útil (letter 21.59 - 2*2.2 cm)

    # ══════════════════════════════════════════════════════════
    # 1. TÍTULO
    # ══════════════════════════════════════════════════════════
    story.append(Spacer(1, 0.3*cm))
    story.append(P("FACTURA DE VENTA", titulo_s))
    story.append(Spacer(1, 0.15*cm))
    story.append(Spacer(1, 0.15*cm))
    story.append(Spacer(1, 0.15*cm))
    story.append(Spacer(1, 0.15*cm))
    story.append(HRFlowable(width="100%", thickness=3, color=AMBER, spaceAfter=0.5*cm))

    # ══════════════════════════════════════════════════════════
    # 2. TABLA DE INFORMACIÓN (2 col: label ámbar | valor blanco)
    # ══════════════════════════════════════════════════════════
    tipo_txt  = "Empresa" if factura["es_empresa"] else "Cliente"
    fecha_fmt = factura['fecha']

    info_rows = [
        [P("Factura N°:",      lbl_s), P(factura['numero'],      val_s)],
        [P("Fecha:",           lbl_s), P(fecha_fmt,              val_s)],
        [P("Cliente/Empresa:", lbl_s), P(factura['cliente'],     val_s)],
        [P("Tipo:",            lbl_s), P(tipo_txt,               val_s)],
        [P("Facturado por:",   lbl_s), P(factura['facturador'],  val_s)],
    ]

    col_lbl = 4.8*cm
    col_val = W - col_lbl

    info_tbl = Table(info_rows, colWidths=[col_lbl, col_val])
    info_tbl.setStyle(TableStyle([
        # Fondo columna izquierda (labels) — ámbar sólido
        ('BACKGROUND',    (0, 0), (0, -1), AMBER),
        # Fondo columna derecha — alterno blanco / ámbar muy claro
        ('ROWBACKGROUNDS',(1, 0), (1, -1), [WHITE, WHITE]),
        # Bordes
        ('BOX',    (0,0), (-1,-1), 1.2, AMBER),
        ('LINEAFTER', (0,0), (0,-1), 1,   AMBER_DARK),
        ('LINEBELOW', (0,0), (-1,-2), 0.5, GRAY_BORDER),
        # Padding
        ('TOPPADDING',    (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING',   (0,0), (-1,-1), 10),
        ('RIGHTPADDING',  (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 0.6*cm))

    # ══════════════════════════════════════════════════════════
    # 3. TABLA DE PRODUCTOS
    # ══════════════════════════════════════════════════════════
    col_nom = 9.0*cm
    col_qty = 2.4*cm
    col_pu  = 3.0*cm
    col_tot = 3.2*cm

    prod_rows = [[
        P("Producto",    hdr_l_s),
        P("Cantidad",    hdr_c_s),
        P("Precio Unit.",hdr_r_s),
        P("Total",       hdr_r_s),
    ]]

    for i, it in enumerate(items):
        subtotal_item = it['precio'] * it['cantidad']
        bg = WHITE if i % 2 == 0 else AMBER_LITE
        prod_rows.append([
            P(it['nombre'],                    cel_l_s),
            P(str(it['cantidad']),             cel_c_s),
            P(f"${it['precio']:,.0f}",         cel_r_s),
            P(f"${subtotal_item:,.0f}",        cel_rb_s),
        ])

    prod_tbl = Table(prod_rows, colWidths=[col_nom, col_qty, col_pu, col_tot])
    n = len(prod_rows)
    row_bgs = [WHITE if i % 2 == 0 else colors.HexColor('#f5f0eb') for i in range(n - 1)]

    prod_tbl.setStyle(TableStyle([
        # Header
        ('BACKGROUND',    (0, 0), (-1, 0),  AMBER_THEAD),
        # Filas alternadas
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), row_bgs),
        # Bordes exteriores e internos
        ('BOX',      (0,0), (-1,-1), 1.2, AMBER),
        ('LINEBELOW',(0, 0), (-1, 0),  1.5, AMBER_DARK),
        ('LINEBELOW',(0, 1), (-1, -2), 0.4, GRAY_BORDER),
        # Padding header (un poco más de aire)
        ('TOPPADDING',    (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 9),
        # Padding filas de datos — compacto
        ('TOPPADDING',    (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        # Padding horizontal
        ('LEFTPADDING',   (0,0), (-1,-1), 9),
        ('RIGHTPADDING',  (0,0), (-1,-1), 9),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(prod_tbl)
    story.append(Spacer(1, 0.5*cm))

    # ══════════════════════════════════════════════════════════
    # 4. SECCIÓN DE TOTALES (alineada a la derecha)
    # ══════════════════════════════════════════════════════════
    tot_col_lbl = 5.5*cm
    tot_col_val = 3.0*cm
    spacer_col  = W - tot_col_lbl - tot_col_val

    tot_rows = []
    tot_rows.append([
        '', 
        P("Subtotal:",  tot_lbl_s), 
        P(f"${factura['subtotal']:,.1f}", tot_val_s)
    ])

    if factura['descuento'] > 0:
        tot_rows.append([
            '',
            P("Descuento 5% (Empresa):", tot_lbl_s),
            P(f"-${factura['descuento']:,.1f}", disc_s)
        ])

    tot_tbl = Table(tot_rows, colWidths=[spacer_col, tot_col_lbl, tot_col_val])
    tot_tbl.setStyle(TableStyle([
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('ALIGN',  (2,0), (2,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(tot_tbl)

    # Línea separadora antes del total
    story.append(HRFlowable(width="100%", thickness=1.5, color=AMBER, spaceBefore=4, spaceAfter=4))

    # Fila TOTAL A PAGAR — tabla independiente para resaltar
    total_row = Table(
        [['', P("TOTAL A PAGAR:", total_lbl), P(f"${factura['total']:,.1f}", total_val)]],
        colWidths=[spacer_col, tot_col_lbl, tot_col_val]
    )
    total_row.setStyle(TableStyle([
        ('TOPPADDING',    (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('ALIGN',  (2,0), (2,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(total_row)
    story.append(Spacer(1, 1*cm))

    # ══════════════════════════════════════════════════════════
    # 5. PIE DE PÁGINA
    # ══════════════════════════════════════════════════════════
    story.append(HRFlowable(width="100%", thickness=1, color=GRAY_BORDER, spaceAfter=6))
    story.append(P("Gracias por tu compra  ·  Ceramicas Artesanales", foot_s))
    story.append(P("Cada pieza es unica y hecha a mano con dedicacion", foot_s))

    doc.build(story)
    buf.seek(0)
    return buf


# ──────────────────────────────────────────
# BASE DE DATOS
# ──────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db(); cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL, precio REAL NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0, categoria TEXT NOT NULL,
            fecha_ingreso TEXT NOT NULL, ventas INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS facturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT NOT NULL UNIQUE, facturador TEXT NOT NULL,
            cliente TEXT NOT NULL, es_empresa INTEGER NOT NULL DEFAULT 0,
            subtotal REAL NOT NULL, descuento REAL NOT NULL DEFAULT 0,
            total REAL NOT NULL, fecha TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS factura_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            factura_id INTEGER NOT NULL, producto_id INTEGER NOT NULL,
            nombre TEXT NOT NULL, precio REAL NOT NULL, cantidad INTEGER NOT NULL,
            FOREIGN KEY (factura_id) REFERENCES facturas(id)
        );
    """)
    cur.execute("SELECT COUNT(*) FROM productos")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO productos (nombre,precio,stock,categoria,fecha_ingreso,ventas) VALUES (?,?,?,?,?,?)",
            [('Unicornio Mediano 1',5700,15,'Alcancías','2025-01-15',45),
             ('Unicornio Mediano 2',6800,8,'Alcancías','2025-01-20',32),
             ('Matera Pequeña',12000,20,'Materas','2025-01-10',28),
             ('Matera Mediana',20000,12,'Materas','2025-02-01',18),
             ('Matera Grande',35000,5,'Materas','2025-02-05',12),
             ('Plato Decorativo',25000,3,'Decoración','2025-02-10',8)])
        cur.executemany(
            "INSERT INTO facturas (numero,facturador,cliente,es_empresa,subtotal,descuento,total,fecha) VALUES (?,?,?,?,?,?,?,?)",
            [('20250301001','Admin','Juan Pérez',0,95000,0,95000,'2025-03-01'),
             ('20250301002','Admin','Cerámica El Arte',1,90000,4500,85500,'2025-03-01')])
    conn.commit(); conn.close()

# ──────────────────────────────────────────
# RUTAS – PÁGINAS
# ──────────────────────────────────────────
@app.route('/')
def index(): return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    conn = get_db()
    productos = [dict(r) for r in conn.execute("SELECT * FROM productos ORDER BY ventas DESC").fetchall()]
    facturas  = [dict(r) for r in conn.execute("SELECT * FROM facturas ORDER BY fecha DESC").fetchall()]
    conn.close()
    return render_template('dashboard.html', productos=productos, facturas=facturas,
        total_mes=sum(f['total'] for f in facturas),
        stock_bajo=[p for p in productos if p['stock']<=5],
        top_vendidos=sorted(productos, key=lambda p: p['ventas'], reverse=True)[:3])

@app.route('/inventario')
def inventario():
    q = request.args.get('q','').strip(); conn = get_db()
    rows = conn.execute("SELECT * FROM productos WHERE nombre LIKE ? ORDER BY nombre",(f'%{q}%',)).fetchall() if q \
           else conn.execute("SELECT * FROM productos ORDER BY nombre").fetchall()
    conn.close()
    return render_template('inventario.html', productos=[dict(r) for r in rows], q=q)

@app.route('/facturacion')
def facturacion():
    conn = get_db()
    productos = [dict(r) for r in conn.execute("SELECT * FROM productos WHERE stock>0 ORDER BY categoria,nombre").fetchall()]
    conn.close()
    return render_template('facturacion.html', productos=productos, categorias=['Alcancías','Materas','Decoración'])

@app.route('/reportes')
def reportes():
    conn = get_db()
    facturas = [dict(r) for r in conn.execute("SELECT * FROM facturas ORDER BY fecha DESC").fetchall()]
    conn.close()
    return render_template('reportes.html', facturas=facturas)

# ──────────────────────────────────────────
# DESCARGA PDF
# ──────────────────────────────────────────
@app.route('/factura/<int:fid>/pdf')
def descargar_factura(fid):
    conn    = get_db()
    factura = conn.execute("SELECT * FROM facturas WHERE id=?", (fid,)).fetchone()
    if not factura: conn.close(); return "Factura no encontrada", 404
    items = [dict(r) for r in conn.execute("SELECT * FROM factura_items WHERE factura_id=?",(fid,)).fetchall()]
    conn.close()
    if not items:
        items = [{'producto_id':'-','nombre':'(sin detalle)','precio':dict(factura)['subtotal'],'cantidad':1}]
    buf  = generar_pdf_factura(dict(factura), items)
    resp = make_response(buf.read())
    resp.headers['Content-Type']        = 'application/pdf'
    resp.headers['Content-Disposition'] = f'attachment; filename=factura_{dict(factura)["numero"]}.pdf'
    return resp

# ──────────────────────────────────────────
# API – PRODUCTOS
# ──────────────────────────────────────────
@app.route('/api/productos', methods=['POST'])
def crear_producto():
    d=request.json; conn=get_db()
    conn.execute("INSERT INTO productos (nombre,precio,stock,categoria,fecha_ingreso,ventas) VALUES (?,?,?,?,?,0)",
        (d['nombre'],float(d['precio']),int(d['stock']),d['categoria'],d['fecha_ingreso']))
    conn.commit(); conn.close(); return jsonify({'ok':True})

@app.route('/api/productos/<int:pid>', methods=['PUT'])
def actualizar_producto(pid):
    d=request.json; conn=get_db()
    conn.execute("UPDATE productos SET nombre=?,precio=?,stock=?,categoria=?,fecha_ingreso=? WHERE id=?",
        (d['nombre'],float(d['precio']),int(d['stock']),d['categoria'],d['fecha_ingreso'],pid))
    conn.commit(); conn.close(); return jsonify({'ok':True})

@app.route('/api/productos/<int:pid>', methods=['DELETE'])
def eliminar_producto(pid):
    conn=get_db(); conn.execute("DELETE FROM productos WHERE id=?",(pid,)); conn.commit(); conn.close(); return jsonify({'ok':True})

@app.route('/api/productos/<int:pid>', methods=['GET'])
def get_producto(pid):
    conn=get_db(); row=conn.execute("SELECT * FROM productos WHERE id=?",(pid,)).fetchone(); conn.close()
    return jsonify(dict(row)) if row else (jsonify({'error':'No encontrado'}),404)

# ──────────────────────────────────────────
# API – FACTURAS
# ──────────────────────────────────────────
@app.route('/api/facturas', methods=['POST'])
def crear_factura():
    d=request.json; items=d['items']; es_emp=bool(d.get('es_empresa',False))
    subtotal=sum(i['precio']*i['cantidad'] for i in items)
    descuento=subtotal*0.05 if es_emp else 0
    total=subtotal-descuento
    numero=datetime.now().strftime('%Y%m%d%H%M%S')
    fecha=datetime.now().strftime('%Y-%m-%d')
    conn=get_db(); cur=conn.cursor()
    cur.execute("INSERT INTO facturas (numero,facturador,cliente,es_empresa,subtotal,descuento,total,fecha) VALUES (?,?,?,?,?,?,?,?)",
        (numero,d['facturador'],d['cliente'],int(es_emp),subtotal,descuento,total,fecha))
    fid=cur.lastrowid
    for item in items:
        cur.execute("INSERT INTO factura_items (factura_id,producto_id,nombre,precio,cantidad) VALUES (?,?,?,?,?)",
            (fid,item['id'],item['nombre'],item['precio'],item['cantidad']))
        cur.execute("UPDATE productos SET stock=stock-?,ventas=ventas+? WHERE id=?",
            (item['cantidad'],item['cantidad'],item['id']))
    conn.commit(); conn.close()
    return jsonify({'ok':True,'id':fid,'numero':numero,'total':total})

if __name__=='__main__':
    init_db()
    app.run(debug=True)
