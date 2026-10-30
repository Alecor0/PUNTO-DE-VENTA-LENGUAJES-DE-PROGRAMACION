"""Interfaz visual de la práctica 8. Ejecutar: python tienda.py"""
import argparse
from decimal import Decimal
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from modelo import Tienda, dinero, entero, ticket


class Aplicacion(tk.Tk):
    def __init__(self, archivo):
        super().__init__()
        self.title('Tienda | Punto de venta')
        self.geometry('1120x760')
        self.minsize(980, 700)
        self.configure(bg='#edf2f7')
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.style.configure('.', font=('Segoe UI', 10))
        self.style.configure('TFrame', background='#edf2f7')
        self.style.configure('TLabel', background='#edf2f7', foreground='#193047')
        self.style.configure('Title.TLabel', font=('Segoe UI', 23, 'bold'))
        self.style.configure('TButton', padding=(12, 8))
        self.style.configure('Accent.TButton', background='#007f78', foreground='white')
        self.style.map('Accent.TButton', background=[('active', '#00665f')])
        self.style.configure('Treeview', rowheight=30, background='white', fieldbackground='white')
        self.style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'), padding=8)
        self.carrito = {}
        self.protocol('WM_DELETE_WINDOW', self.cerrar)
        try:
            self.modelo = Tienda(archivo)
        except (ValueError, OSError) as error:
            messagebox.showerror('No se pudo abrir la tienda', str(error), parent=self)
            self.destroy()
            raise
        self.mostrar_login()

    def limpiar(self):
        for widget in self.winfo_children():
            widget.destroy()

    def proteger(self, funcion):
        try:
            return funcion()
        except (ValueError, PermissionError, OSError) as error:
            messagebox.showerror('Revisa los datos', str(error), parent=self)

    def mostrar_login(self):
        self.limpiar()
        self.modelo.salir()
        self.carrito.clear()
        cont = ttk.Frame(self, padding=36)
        cont.place(relx=.5, rely=.45, anchor='center')
        ttk.Label(cont, text='TIENDA', style='Title.TLabel').pack(anchor='w')
        ttk.Label(cont, text='Papelería · Punto de venta', padding=(0, 8, 0, 25)).pack(anchor='w')
        self.usuario = tk.StringVar()
        self.clave = tk.StringVar()
        for etiqueta, variable, oculto in [('Usuario', self.usuario, ''), ('Contraseña', self.clave, '•')]:
            ttk.Label(cont, text=etiqueta).pack(anchor='w', pady=(8, 4))
            entrada = ttk.Entry(cont, textvariable=variable, show=oculto, width=34)
            entrada.pack(ipady=5)
            entrada.bind('<Return>', lambda e: self.proteger(self.iniciar))
        ttk.Button(cont, text='Iniciar sesión', style='Accent.TButton',
                   command=lambda: self.proteger(self.iniciar)).pack(fill='x', pady=22)
        ttk.Label(cont, text='Cuentas de demostración en LEEME.md').pack()

    def iniciar(self):
        self.modelo.entrar(self.usuario.get(), self.clave.get())
        self.clave.set('')
        self.mostrar_principal()

    def mostrar_principal(self):
        self.limpiar()
        cabecera = ttk.Frame(self, padding=(24, 18))
        cabecera.pack(fill='x')
        ttk.Label(cabecera, text='Tienda', style='Title.TLabel').pack(side='left')
        ttk.Button(cabecera, text='Cerrar sesión', command=self.cerrar_sesion).pack(side='right')
        ttk.Label(cabecera, text=f'{self.modelo.usuario} · {self.modelo.rol}  ').pack(side='right', padx=16)
        self.pestanas = ttk.Notebook(self)
        self.pestanas.pack(fill='both', expand=True, padx=24, pady=(0, 12))
        self.venta_tab = ttk.Frame(self.pestanas, padding=18)
        self.pestanas.add(self.venta_tab, text='  Nueva venta  ')
        self.crear_venta()
        self.catalogos = {}
        self.crear_catalogo('clientes')
        self.crear_catalogo('productos')
        self.crear_historial()
        ttk.Label(self, text='Importes en MXN · IVA 16 % · Guardado local en JSON', padding=(24, 0, 0, 12)).pack(anchor='w')
        self.refrescar()

    def tabla(self, padre, columnas, anchos=None, alto=7):
        marco = ttk.Frame(padre)
        marco.pack(fill='both', expand=True, pady=8)
        arbol = ttk.Treeview(marco, columns=columnas, show='headings', height=alto, selectmode='browse')
        for i, columna in enumerate(columnas):
            arbol.heading(columna, text=columna)
            arbol.column(columna, width=anchos[i] if anchos else 140, minwidth=65)
        barra = ttk.Scrollbar(marco, orient='vertical', command=arbol.yview)
        arbol.configure(yscrollcommand=barra.set)
        barra.pack(side='right', fill='y')
        arbol.pack(fill='both', expand=True)
        return arbol

    def crear_venta(self):
        p = self.venta_tab
        ttk.Label(p, text='Selecciona un cliente y agrega artículos por su código.').pack(anchor='w')
        fila = ttk.Frame(p)
        fila.pack(fill='x', pady=10)
        ttk.Label(fila, text='Cliente').pack(side='left', padx=(0, 10))
        self.cliente_combo = ttk.Combobox(fila, state='readonly', width=55)
        self.cliente_combo.pack(side='left')
        fila = ttk.Frame(p)
        fila.pack(fill='x', pady=8)
        ttk.Label(fila, text='Producto').pack(side='left', padx=(0, 10))
        self.producto_combo = ttk.Combobox(fila, state='readonly', width=49)
        self.producto_combo.pack(side='left')
        ttk.Label(fila, text='Cantidad').pack(side='left', padx=12)
        self.cantidad = tk.StringVar(value='1')
        ttk.Entry(fila, textvariable=self.cantidad, width=7).pack(side='left', ipady=4)
        ttk.Button(fila, text='Agregar', style='Accent.TButton', command=lambda: self.proteger(self.agregar)).pack(side='left', padx=12)
        self.carrito_tabla = self.tabla(p, ('Código', 'Producto', 'Cantidad', 'P. unitario', 'Importe'), [90, 330, 90, 130, 130])
        acciones = ttk.Frame(p)
        acciones.pack(fill='x')
        ttk.Button(acciones, text='Quitar seleccionado', command=self.quitar).pack(side='left')
        ttk.Button(acciones, text='Vaciar carrito', command=self.vaciar).pack(side='left', padx=8)
        self.totales = tk.StringVar(value='Subtotal: $0.00     IVA: $0.00     Total: $0.00')
        ttk.Label(p, textvariable=self.totales, font=('Segoe UI', 15, 'bold')).pack(anchor='e', pady=18)
        pago_fila = ttk.Frame(p)
        pago_fila.pack(fill='x')
        ttk.Label(pago_fila, text='Efectivo recibido $').pack(side='left')
        self.pago = tk.StringVar()
        ttk.Entry(pago_fila, textvariable=self.pago, width=16).pack(side='left', padx=12, ipady=5)
        ttk.Button(pago_fila, text='Cobrar y generar ticket', style='Accent.TButton',
                   command=lambda: self.proteger(self.cobrar)).pack(side='right')

    def crear_catalogo(self, tipo):
        p = ttk.Frame(self.pestanas, padding=18)
        self.pestanas.add(p, text=f'  {tipo.capitalize()}  ')
        admin = self.modelo.rol == 'administrador'
        ttk.Label(p, text='Selecciona una fila para consultar o editar sus datos.').pack(anchor='w')
        campos = [('Código', 'codigo'), ('Nombre', 'nombre')]
        campos += [('Precio sin IVA', 'precio'), ('Existencias', 'existencias')] if tipo == 'productos' else [
            ('Teléfono', 'telefono'), ('Correo', 'correo'), ('Dirección', 'direccion')]
        form = ttk.Frame(p)
        form.pack(fill='x', pady=10)
        variables, entradas = {}, {}
        for i, (etiqueta, campo) in enumerate(campos):
            grupo = ttk.Frame(form)
            grupo.grid(row=i // 3, column=i % 3, sticky='ew', padx=(0, 12), pady=4)
            form.columnconfigure(i % 3, weight=1)
            ttk.Label(grupo, text=etiqueta).pack(anchor='w')
            variables[campo] = tk.StringVar()
            entradas[campo] = ttk.Entry(grupo, textvariable=variables[campo])
            entradas[campo].pack(fill='x', ipady=4)
        columnas = ('Código', 'Nombre', 'Precio', 'Existencias') if tipo == 'productos' else ('Código', 'Nombre', 'Teléfono', 'Correo', 'Dirección')
        arbol = self.tabla(p, columnas)
        estado = {'variables': variables, 'entradas': entradas, 'tabla': arbol, 'editar': False}
        self.catalogos[tipo] = estado
        arbol.bind('<<TreeviewSelect>>', lambda e: self.seleccionar_catalogo(tipo))
        botones = ttk.Frame(p)
        botones.pack(fill='x', pady=8)
        puede_crear = admin or tipo == 'clientes'
        ttk.Button(botones, text='Nuevo / Limpiar', command=lambda: self.limpiar_formulario(tipo)).pack(side='left')
        guardar = ttk.Button(botones, text='Guardar', style='Accent.TButton', command=lambda: self.proteger(lambda: self.guardar_catalogo(tipo)))
        guardar.pack(side='left', padx=8)
        if not puede_crear:
            guardar.state(['disabled'])
            for entrada in entradas.values():
                entrada.state(['disabled'])
        baja = ttk.Button(botones, text='Dar de baja', command=lambda: self.proteger(lambda: self.baja(tipo)))
        baja.pack(side='left')
        if not admin:
            baja.state(['disabled'])
            ttk.Label(p, text='Cajero: consulta productos y registra clientes nuevos. El administrador edita y da de baja.').pack(anchor='w', pady=8)

    def limpiar_formulario(self, tipo):
        e = self.catalogos[tipo]
        e['editar'] = False
        e['tabla'].selection_remove(e['tabla'].selection())
        e['entradas']['codigo'].configure(state='normal' if self.modelo.rol == 'administrador' or tipo == 'clientes' else 'disabled')
        for variable in e['variables'].values():
            variable.set('')

    def seleccionar_catalogo(self, tipo):
        e = self.catalogos[tipo]
        seleccion = e['tabla'].selection()
        if not seleccion:
            return
        codigo = seleccion[0]
        registro = self.modelo.catalogo(tipo)[codigo]
        e['editar'] = True
        e['variables']['codigo'].set(codigo)
        e['entradas']['codigo'].configure(state='readonly')
        for campo, variable in e['variables'].items():
            if campo != 'codigo':
                variable.set(registro[campo])

    def guardar_catalogo(self, tipo):
        e = self.catalogos[tipo]
        valores = {k: v.get() for k, v in e['variables'].items()}
        if tipo == 'productos':
            self.modelo.guardar_producto(**valores, editar=e['editar'])
        else:
            self.modelo.guardar_cliente(**valores, editar=e['editar'])
        self.limpiar_formulario(tipo)
        self.refrescar()

    def baja(self, tipo):
        seleccion = self.catalogos[tipo]['tabla'].selection()
        if not seleccion:
            raise ValueError('Selecciona un registro.')
        if messagebox.askyesno('Dar de baja', '¿Dar de baja el registro seleccionado?', parent=self):
            self.modelo.eliminar(tipo, seleccion[0])
            self.limpiar_formulario(tipo)
            self.refrescar()

    def crear_historial(self):
        p = ttk.Frame(self.pestanas, padding=18)
        self.pestanas.add(p, text='  Historial de ventas  ')
        ttk.Label(p, text='Ventas guardadas · Selecciona una para consultar su nota digital.').pack(anchor='w')
        self.ventas_tabla = self.tabla(p, ('Folio', 'Fecha', 'Cliente', 'Cajero', 'Total'))
        ttk.Button(p, text='Ver / Guardar ticket', command=lambda: self.proteger(self.abrir_historial)).pack(anchor='e')

    @staticmethod
    def llenar(arbol, filas):
        arbol.delete(*arbol.get_children())
        for clave, valores in filas:
            arbol.insert('', 'end', iid=clave, values=valores)

    def refrescar(self):
        clientes = self.modelo.catalogo('clientes')
        productos = self.modelo.catalogo('productos')
        for tipo, registros in [('clientes', clientes), ('productos', productos)]:
            campos = ['nombre', 'precio', 'existencias'] if tipo == 'productos' else ['nombre', 'telefono', 'correo', 'direccion']
            self.llenar(self.catalogos[tipo]['tabla'], [(k, [k] + [r[c] for c in campos]) for k, r in registros.items()])
        actual = self.cliente_combo.get().split(' | ')[0]
        opciones = [f'{k} | {r["nombre"]}' for k, r in clientes.items()]
        self.cliente_combo['values'] = opciones
        self.cliente_combo.set(next((o for o in opciones if o.split(' | ')[0] == actual), opciones[0] if opciones else ''))
        self.producto_combo['values'] = [f'{k} | {r["nombre"]} | ${r["precio"]} | Stock: {r["existencias"]}' for k, r in productos.items()]
        self.producto_combo.set('')
        self.llenar(self.ventas_tabla, [(v['folio'], [v['folio'], v['fecha'][:19].replace('T', ' '), v['cliente'], v['usuario'], '$' + v['total']]) for v in reversed(self.modelo.historial())])
        # Si el administrador baja un producto del carrito, lo retira antes de cotizar.
        self.carrito = {k: min(c, productos[k]['existencias']) for k, c in self.carrito.items()
                        if k in productos and productos[k]['existencias'] > 0}
        self.actualizar_carrito()

    def agregar(self):
        codigo = self.producto_combo.get().split(' | ')[0]
        if not codigo:
            raise ValueError('Selecciona un producto del catálogo.')
        nuevo = dict(self.carrito)
        nuevo[codigo] = nuevo.get(codigo, 0) + entero(self.cantidad.get(), 1)
        self.modelo.cotizar(nuevo)
        self.carrito = nuevo
        self.actualizar_carrito()

    def actualizar_carrito(self):
        if not self.carrito:
            self.llenar(self.carrito_tabla, [])
            self.totales.set('Subtotal: $0.00     IVA: $0.00     Total: $0.00')
            return
        cotizacion = self.modelo.cotizar(self.carrito)
        self.llenar(self.carrito_tabla, [(d['codigo'], [d['codigo'], d['producto'], d['cantidad'], '$' + d['precio'], '$' + d['importe']]) for d in cotizacion['detalles']])
        self.totales.set(f'Subtotal: ${cotizacion["subtotal"]}     IVA: ${cotizacion["iva"]}     Total: ${cotizacion["total"]}')

    def quitar(self):
        seleccion = self.carrito_tabla.selection()
        if seleccion:
            self.carrito.pop(seleccion[0], None)
            self.actualizar_carrito()

    def vaciar(self):
        self.carrito.clear()
        self.actualizar_carrito()

    def cobrar(self):
        cliente = self.cliente_combo.get().split(' | ')[0]
        cotizacion = self.modelo.cotizar(self.carrito)
        if dinero(self.pago.get()) < Decimal(cotizacion['total']):
            raise ValueError('El pago es insuficiente para cubrir el total.')
        if not messagebox.askyesno('Confirmar venta', f'¿Registrar el cobro por ${cotizacion["total"]}?', parent=self):
            return
        venta = self.modelo.vender(cliente, self.carrito, self.pago.get())
        self.carrito.clear()
        self.pago.set('')
        self.refrescar()
        self.mostrar_ticket(venta)

    def abrir_historial(self):
        seleccion = self.ventas_tabla.selection()
        if not seleccion:
            raise ValueError('Selecciona una venta del historial.')
        venta = next(v for v in self.modelo.historial() if v['folio'] == seleccion[0])
        self.mostrar_ticket(venta)

    def mostrar_ticket(self, venta):
        ventana = tk.Toplevel(self)
        ventana.title(f'Ticket {venta["folio"]}')
        ventana.geometry('720x600')
        contenido = tk.Text(ventana, font=('Consolas', 11), padx=18, pady=18, wrap='word')
        barra = ttk.Scrollbar(ventana, orient='vertical', command=contenido.yview)
        barra.pack(side='right', fill='y')
        contenido.configure(yscrollcommand=barra.set)
        contenido.pack(fill='both', expand=True)
        contenido.insert('1.0', ticket(venta))
        contenido.configure(state='disabled')
        ttk.Button(ventana, text='Guardar ticket .txt', command=lambda: self.proteger(lambda: self.exportar(venta))).pack(pady=12)

    def exportar(self, venta):
        ruta = filedialog.asksaveasfilename(parent=self, title='Guardar ticket digital',
                                           defaultextension='.txt', initialfile=venta['folio'] + '.txt',
                                           filetypes=[('Archivo de texto', '*.txt')])
        if ruta:
            Path(ruta).write_text(ticket(venta), encoding='utf-8')
            messagebox.showinfo('Ticket guardado', f'Se guardó el ticket en:\n{ruta}', parent=self)

    def cerrar_sesion(self):
        if self.carrito and not messagebox.askyesno('Cerrar sesión', 'Se descartará el carrito pendiente. ¿Continuar?', parent=self):
            return
        self.mostrar_login()

    def cerrar(self):
        if self.carrito and not messagebox.askyesno('Salir', 'Se descartará el carrito pendiente. ¿Salir?', parent=self):
            return
        self.destroy()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Práctica 8: Tienda con interfaz gráfica y JSON.')
    parser.add_argument('--datos', type=Path, default=Path(__file__).resolve().parent / 'datos' / 'tienda.json')
    argumentos = parser.parse_args()
    Aplicacion(argumentos.datos).mainloop()
