"""Reglas de la tienda y persistencia JSON, sin base de datos."""
from __future__ import annotations

import copy
import hashlib
import hmac
import json
import os
import re
import secrets
import tempfile
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

IVA = Decimal('0.16')
CENTAVO = Decimal('0.01')


def dinero(valor):
    """Convierte texto o números a pesos con dos decimales."""
    try:
        numero = Decimal(str(valor).strip())
        if not numero.is_finite() or not 0 <= numero <= 999_999_999:
            raise ValueError('El importe debe estar entre 0 y 999999999.')
        return numero.quantize(CENTAVO, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError):
        raise ValueError('Escribe un importe válido, por ejemplo 25.50.') from None


def entero(valor, minimo=0):
    texto = str(valor).strip()
    if not re.fullmatch(r'\d+', texto) or not minimo <= int(texto) <= 999_999:
        raise ValueError(f'Escribe un número entero entre {minimo} y 999999.')
    return int(texto)


def texto(valor, campo, maximo=120):
    valor = str(valor).strip()
    if not valor or len(valor) > maximo or any(ord(c) < 32 for c in valor):
        raise ValueError(f'{campo}: escribe entre 1 y {maximo} caracteres sin saltos de línea.')
    return valor


def clave_hash(clave, sal):
    return hashlib.pbkdf2_hmac('sha256', clave.encode(), bytes.fromhex(sal), 120_000).hex()


def datos_iniciales():
    usuarios = {}
    for nombre, clave, rol in [('admin', 'Admin123!', 'administrador'),
                                ('cajero', 'Caja123!', 'cajero')]:
        sal = secrets.token_hex(16)
        usuarios[nombre] = {'sal': sal, 'hash': clave_hash(clave, sal), 'rol': rol}
    return {'version': 1, 'usuarios': usuarios,
            'clientes': {'C001': {'nombre': 'Público general', 'telefono': '',
                                 'correo': '', 'direccion': '', 'activo': True}},
            'productos': {
                'P001': {'nombre': 'Cuaderno profesional', 'precio': '35.00', 'existencias': 50, 'activo': True},
                'P002': {'nombre': 'Bolígrafo azul', 'precio': '10.00', 'existencias': 100, 'activo': True},
                'P003': {'nombre': 'Lápiz HB', 'precio': '8.00', 'existencias': 80, 'activo': True},
                'P004': {'nombre': 'Carpeta tamaño carta', 'precio': '25.00', 'existencias': 30, 'activo': True}},
            'ventas': []}


class Tienda:
    def __init__(self, archivo):
        self.archivo = Path(archivo)
        self.usuario = None
        self.rol = None
        if self.archivo.exists():
            try:
                self.datos = json.loads(self.archivo.read_text(encoding='utf-8'))
                if self.datos['version'] != 1:
                    raise ValueError('Versión de archivo desconocida.')
                for campo, tipo in [('usuarios', dict), ('clientes', dict),
                                    ('productos', dict), ('ventas', list)]:
                    if not isinstance(self.datos[campo], tipo):
                        raise ValueError('Estructura incorrecta.')
            except (ValueError, KeyError, TypeError) as error:
                raise ValueError(f'No se puede leer {self.archivo}. Conserva el archivo y revisa su contenido: {error}') from error
        else:
            self.datos = datos_iniciales()
            self._guardar(self.datos)

    def _guardar(self, datos):
        """Reemplazo atómico: un fallo de escritura conserva el estado anterior."""
        self.archivo.parent.mkdir(parents=True, exist_ok=True)
        temporal = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                             dir=self.archivo.parent, delete=False) as salida:
                temporal = Path(salida.name)
                json.dump(datos, salida, ensure_ascii=False, indent=2, allow_nan=False)
                salida.flush()
                os.fsync(salida.fileno())
            os.replace(temporal, self.archivo)
        finally:
            if temporal is not None and temporal.exists():
                temporal.unlink()

    def _confirmar(self, nuevos):
        self._guardar(nuevos)
        self.datos = nuevos

    def entrar(self, usuario, clave):
        self.salir()
        registro = self.datos['usuarios'].get(usuario.strip())
        if not registro or not hmac.compare_digest(registro['hash'], clave_hash(clave, registro['sal'])):
            raise ValueError('Usuario o contraseña incorrectos.')
        self.usuario, self.rol = usuario.strip(), registro['rol']

    def salir(self):
        self.usuario = self.rol = None

    def _autorizar(self, administrador=False):
        if not self.usuario:
            raise PermissionError('Primero inicia sesión.')
        if administrador and self.rol != 'administrador':
            raise PermissionError('Esta acción requiere el rol de administrador.')

    def catalogo(self, tipo):
        self._autorizar()
        if tipo not in ('clientes', 'productos'):
            raise ValueError('Catálogo desconocido.')
        return copy.deepcopy({k: v for k, v in self.datos[tipo].items() if v['activo']})

    def guardar_cliente(self, codigo, nombre, telefono='', correo='', direccion='', editar=False):
        self._autorizar()
        if editar:
            self._autorizar(administrador=True)
        codigo = texto(codigo, 'Código', 20).upper()
        if not re.fullmatch(r'[A-Z0-9_-]+', codigo):
            raise ValueError('El código solo admite letras, números, guion y guion bajo.')
        existe = codigo in self.datos['clientes']
        if existe != editar:
            raise ValueError('El código ya existe.' if existe else 'El cliente no existe.')
        if existe and not self.datos['clientes'][codigo]['activo']:
            raise ValueError('El cliente está dado de baja; utiliza otro código.')
        correo = correo.strip()
        if correo and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', correo):
            raise ValueError('El correo no tiene un formato válido.')
        nuevo = {'nombre': texto(nombre, 'Nombre', 80), 'telefono': telefono.strip(),
                 'correo': correo, 'direccion': direccion.strip(), 'activo': True}
        for campo in ('telefono', 'correo', 'direccion'):
            if nuevo[campo]:
                nuevo[campo] = texto(nuevo[campo], campo, 120)
        datos = copy.deepcopy(self.datos)
        datos['clientes'][codigo] = nuevo
        self._confirmar(datos)

    def guardar_producto(self, codigo, nombre, precio, existencias, editar=False):
        self._autorizar(administrador=True)
        codigo = texto(codigo, 'Código', 20).upper()
        if not re.fullmatch(r'[A-Z0-9_-]+', codigo):
            raise ValueError('El código solo admite letras, números, guion y guion bajo.')
        existe = codigo in self.datos['productos']
        if existe != editar:
            raise ValueError('El código ya existe.' if existe else 'El producto no existe.')
        if existe and not self.datos['productos'][codigo]['activo']:
            raise ValueError('El producto está dado de baja; utiliza otro código.')
        precio = dinero(precio)
        if precio <= 0:
            raise ValueError('El precio debe ser mayor que cero.')
        datos = copy.deepcopy(self.datos)
        datos['productos'][codigo] = {'nombre': texto(nombre, 'Nombre', 80),
            'precio': str(precio), 'existencias': entero(existencias), 'activo': True}
        self._confirmar(datos)

    def eliminar(self, tipo, codigo):
        self._autorizar(administrador=True)
        if tipo not in ('clientes', 'productos') or codigo not in self.datos[tipo]:
            raise ValueError('Selecciona un registro válido.')
        if tipo == 'clientes' and codigo == 'C001':
            raise ValueError('El cliente Público general debe permanecer disponible.')
        datos = copy.deepcopy(self.datos)
        datos[tipo][codigo]['activo'] = False
        self._confirmar(datos)

    def cotizar(self, carrito):
        self._autorizar()
        if not carrito:
            raise ValueError('Agrega al menos un producto.')
        detalles = []
        for codigo, cantidad in carrito.items():
            producto = self.datos['productos'].get(codigo)
            if not producto or not producto['activo']:
                raise ValueError(f'El producto {codigo} no está disponible.')
            cantidad = entero(cantidad, 1)
            if cantidad > producto['existencias']:
                raise ValueError(f'Existencias insuficientes para {producto["nombre"]}.')
            precio = Decimal(producto['precio'])
            importe = (precio * cantidad).quantize(CENTAVO)
            detalles.append({'codigo': codigo, 'producto': producto['nombre'],
                             'cantidad': cantidad, 'precio': str(precio), 'importe': str(importe)})
        subtotal = sum((Decimal(d['importe']) for d in detalles), Decimal('0.00'))
        iva = (subtotal * IVA).quantize(CENTAVO, rounding=ROUND_HALF_UP)
        return {'detalles': detalles, 'subtotal': str(subtotal), 'iva': str(iva), 'total': str(subtotal + iva)}

    def vender(self, cliente, carrito, pago):
        self._autorizar()
        registro = self.datos['clientes'].get(cliente)
        if not registro or not registro['activo']:
            raise ValueError('Selecciona un cliente disponible.')
        venta = self.cotizar(carrito)
        pago = dinero(pago)
        if pago < Decimal(venta['total']):
            raise ValueError('El pago es insuficiente para cubrir el total.')
        venta.update({'folio': f'V{len(self.datos["ventas"]) + 1:06d}',
                      'fecha': datetime.now().astimezone().isoformat(timespec='seconds'),
                      'cliente_codigo': cliente, 'cliente': registro['nombre'],
                      'usuario': self.usuario, 'pago': str(pago),
                      'cambio': str(pago - Decimal(venta['total']))})
        datos = copy.deepcopy(self.datos)
        for detalle in venta['detalles']:
            datos['productos'][detalle['codigo']]['existencias'] -= detalle['cantidad']
        datos['ventas'].append(venta)
        self._confirmar(datos)
        return copy.deepcopy(venta)

    def historial(self):
        self._autorizar()
        return copy.deepcopy(self.datos['ventas'])


def ticket(venta):
    lineas = ['TIENDA | PAPELERÍA', 'NOTA DE VENTA DIGITAL', '=' * 60,
              f'Folio: {venta["folio"]}', f'Fecha: {venta["fecha"]}',
              f'Cliente: {venta["cliente"]} ({venta["cliente_codigo"]})',
              f'Atendió: {venta["usuario"]}', '-' * 60]
    for d in venta['detalles']:
        lineas.extend([f'{d["codigo"]} | {d["producto"]}',
                       f'  {d["cantidad"]} x ${d["precio"]} = ${d["importe"]}'])
    lineas.extend(['-' * 60, f'Subtotal: ${venta["subtotal"]}', f'IVA (16 %): ${venta["iva"]}',
                   f'TOTAL: ${venta["total"]}', f'Pago: ${venta["pago"]}',
                   f'Cambio: ${venta["cambio"]}', '=' * 60, 'Gracias por tu compra.',
                   'Proyecto académico. Precios antes de IVA; importes en MXN.'])
    return '\n'.join(lineas) + '\n'
