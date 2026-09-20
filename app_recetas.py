# app_recetas.py
# Autor: SaintWick
"""
Módulo de recetas de Cervecera VGB (split de app_gestion.py, que había vuelto
a crecer demasiado tras sumar Comunidad).

Contiene RecetasMixin:
- CRUD de recetas (cargar lista, seleccionar, nueva, guardar, eliminar).
- Import/export: JSON, PDF, BeerXML, recetario web y auto-actualización.
- Comunidad: compartir/descargar recetas vía GitHub (Contents API).
- Chrome de la UI: menú "☰ Menú", toggle de "Mis Recetas", manual de
  usuario y visor de log.

Importa utilidades y constantes compartidas desde app_gestion.py (que no
depende de este archivo ni de app.py, así que no hay import circular).

Se combina con la clase principal en app.py por herencia múltiple:
    class CerveceraApp(GestionMixin, RecetasMixin, ctk.CTk): ...
"""
import customtkinter as ctk
import tkinter.messagebox as mb
from tkinter import filedialog
import json
import os
import sys
import subprocess
import threading
import tempfile
import base64
import urllib.request
import urllib.error
import re
from logger import logger
from app_paths import get_data_dir
from brew_engine import BrewEngine
from bjcp_styles import get_style_list
from catalogo_ar import LEVADURAS_AR, ALTITUDES_CORDOBA, PERFILES_AGUA_CORDOBA
from export_engine import exportar_pdf, exportar_beerxml
from app_gestion import (format_num, resource_path, _huella, AyudaDialog,
                         APP_VERSION, RECETARIO_URL, RELEASE_API_URL,
                         COMUNIDAD_LISTADO_URL, COMUNIDAD_ARCHIVO_URL,
                         COMUNIDAD_TOKEN_ENV, COMUNIDAD_TOKEN_FILE,
                         VOLUMENES_PRESET, DEF_PERFIL_AGUA, DEF_LEVADURA,
                         DEF_ALTITUD, DEF_FORMATO)


class RecetasMixin:
    # ==========================================
    # LISTA / SELECCIÓN / NUEVA / GUARDAR
    # ==========================================
    def cargar_lista_recetas(self):
        for w in self.lista_recetas.winfo_children():
            w.destroy()
        for r in self.db.get_all_recipes_summary():
            ctk.CTkButton(self.lista_recetas,
                          text=f"{r['name']} ({r['volume']}L)",
                          fg_color="transparent", border_width=1,
                          text_color=("gray10", "gray90"),
                          hover_color=("gray70", "gray30"), anchor="w",
                          command=lambda r_id=r['id']: self.seleccionar_receta(r_id)
                          ).pack(pady=5, padx=5, fill="x")

    def seleccionar_receta(self, receta_id):
        receta = self.db.get_full_recipe(receta_id)
        if not receta: return
        self.receta_actual_id = receta_id
        self.entry_nombre.delete(0, "end"); self.entry_nombre.insert(0, receta['name'])
        self.volumen_base_receta = float(receta['volume'])
        vol_str = str(int(self.volumen_base_receta))
        self.combo_volumen.set(vol_str if vol_str in VOLUMENES_PRESET else vol_str)
        self.entry_eficiencia.delete(0, "end")
        self.entry_eficiencia.insert(0, str(int(round(float(receta['efficiency']) * 100))))
        self.texto_notas.delete("1.0", "end"); self.texto_notas.insert(1.0, receta.get('notes', ''))
        # Estilo BJCP guardado
        estilo_saved = receta.get('style') or "Auto (Sugerir)"
        self.combo_estilo_bjcp.set(estilo_saved if estilo_saved in get_style_list() else "Auto (Sugerir)")
        # Altitud / levadura / maceración / hervor (paridad móvil)
        alt_nombre = receta.get('altitud_name') or DEF_ALTITUD
        if alt_nombre in ALTITUDES_CORDOBA:
            self.combo_altitud.set(alt_nombre)
        self.entry_so4.delete(0, "end"); self.entry_so4.insert(0, format_num(receta.get('agua_so4', 0) or 0))
        self.entry_cl.delete(0, "end");  self.entry_cl.insert(0, format_num(receta.get('agua_cl', 0) or 0))
        obj_g = receta.get('agua_objetivo') or "Balanceada (genérica)"
        if obj_g in BrewEngine.PERFILES_AGUA_OBJETIVO:
            self.combo_agua_obj.set(obj_g)
        eq_nombre = receta.get('equipo') or ''
        if eq_nombre and eq_nombre in self._nombres_equipos():
            self.combo_equipo.set(eq_nombre)
        self.entry_ratio.delete(0, "end")
        self.entry_ratio.insert(0, format_num(receta.get('ratio_maceracion', 3.0)))
        self.entry_absorcion.delete(0, "end")
        self.entry_absorcion.insert(0, format_num(receta.get('absorcion', 1.0)))
        self.entry_hervor.delete(0, "end")
        self.entry_hervor.insert(0, format_num(receta.get('tiempo_hervor', 60)))
        # Levadura guardada
        levadura_saved = None
        if receta.get('levaduras'):
            levadura_saved = receta['levaduras'][0].get('name')
        if levadura_saved and levadura_saved in LEVADURAS_AR:
            self.combo_levadura.set(levadura_saved)
        # Perfil de agua guardado (Ca/Mg/HCO3/pH)
        ca_s, mg_s, hc_s = (receta.get('agua_ca'), receta.get('agua_mg'), receta.get('agua_hco3'))
        perfil_match = None
        if None not in (ca_s, mg_s, hc_s):
            perfil_match = next((k for k, v in PERFILES_AGUA_CORDOBA.items()
                                 if abs(v.get('ca', 0) - ca_s) < 0.01
                                 and abs(v.get('mg', 0) - mg_s) < 0.01
                                 and abs(v.get('hco3', 0) - hc_s) < 0.01), None)
            if perfil_match:
                self.combo_agua.set(perfil_match)
        self.entry_ca.delete(0, "end");   self.entry_ca.insert(0, format_num(ca_s if ca_s is not None else 50))
        self.entry_mg.delete(0, "end");   self.entry_mg.insert(0, format_num(mg_s if mg_s is not None else 10))
        self.entry_hco3.delete(0, "end"); self.entry_hco3.insert(0, format_num(hc_s if hc_s is not None else 150))
        ph_entrada = receta.get('agua_ph_entrada')
        if ph_entrada is not None:
            self.entry_ph_agua.delete(0, "end"); self.entry_ph_agua.insert(0, format_num(ph_entrada))
        elif perfil_match:
            ph = PERFILES_AGUA_CORDOBA[perfil_match].get('ph', 7.0)
            self.entry_ph_agua.delete(0, "end"); self.entry_ph_agua.insert(0, format_num(ph))
        else:
            self.entry_ph_agua.delete(0, "end"); self.entry_ph_agua.insert(0, "7.0")
        # Ingredientes (maltas con color, lúpulos con formato)
        for w in self.frame_lista_maltas.winfo_children(): w.destroy()
        for w in self.frame_lista_lupulos.winfo_children(): w.destroy()
        for m in receta['maltas']:
            self.add_fila_malta({'nombre': m['name'], 'cantidad': float(m['amount']),
                                 'extracto': float(m.get('extract', 300)),
                                 'color': float(m.get('color', 2))})
        for l in receta['lupulos']:
            self.add_fila_lupulo({'nombre': l['name'], 'cantidad': float(l['amount']),
                                  'aa': float(l['alpha_acids']),
                                  'tiempo': float(l['time']),
                                  'formato': l.get('formato', DEF_FORMATO)})
        self.tabview.set("🛠️ Receta")
        self.calcular_y_mostrar()

    def nueva_receta(self):
        self.receta_actual_id = None
        self.entry_nombre.delete(0, "end")
        self.combo_volumen.set("20")
        self.volumen_base_receta = 20.0
        self.entry_eficiencia.delete(0, "end"); self.entry_eficiencia.insert(0, "75")
        self.combo_altitud.set(DEF_ALTITUD)
        self.combo_levadura.set(DEF_LEVADURA if DEF_LEVADURA in LEVADURAS_AR else sorted(LEVADURAS_AR.keys())[0])
        self.combo_estilo_bjcp.set("Auto (Sugerir)")
        self.entry_ratio.delete(0, "end");     self.entry_ratio.insert(0, "3.0")
        self.entry_absorcion.delete(0, "end"); self.entry_absorcion.insert(0, "1.0")
        self.entry_hervor.delete(0, "end");    self.entry_hervor.insert(0, "60")
        self.combo_agua.set(DEF_PERFIL_AGUA)
        self.entry_so4.delete(0, "end"); self.entry_so4.insert(0, "0")
        self.entry_cl.delete(0, "end");  self.entry_cl.insert(0, "0")
        self.combo_agua_obj.set("Balanceada (genérica)")
        self._on_perfil_agua(None)
        self.texto_notas.delete("1.0", "end")
        self._reset_panel_resultados()
        for w in self.frame_lista_maltas.winfo_children(): w.destroy()
        for w in self.frame_lista_lupulos.winfo_children(): w.destroy()

    def guardar_receta(self):
        nombre = self.entry_nombre.get().strip()
        if not nombre:
            mb.showwarning("Atención", "Escribe un nombre."); return
        maltas, lupulos = self.leer_ingredientes_ui()
        if not maltas and not lupulos:
            mb.showwarning("Atención", "Receta vacía."); return
        resultados = self.calcular_y_mostrar()
        if not resultados: return
        volumen, eficiencia, ratio, absorcion, tiempo_hervor, altitud = self._leer_parametros()
        levadura_nombre, levadura_datos = self._leer_levadura()
        agua_datos = self._leer_agua_ui()
        notas = self.texto_notas.get("1.0", "end-1c").strip()
        r = resultados['r']
        receta_data = {
            'name': nombre, 'style': self.combo_estilo_bjcp.get(),
            'volume': volumen, 'efficiency': eficiencia,
            'og_estimated': r['og'], 'fg_estimated': r['fg'],
            'ibu_estimated': r['ibu'], 'srm_estimated': r['srm'],
            'notes': notas,
            'maltas': maltas, 'lupulos': lupulos,
            'levaduras': [{'nombre': levadura_nombre,
                           'atenuacion': levadura_datos['atenuacion'],
                           'tolerancia': levadura_datos['tolerancia_abv']}],
            'agua_ca': agua_datos['ca'], 'agua_mg': agua_datos['mg'],
            'agua_hco3': agua_datos['hco3'], 'agua_ph_entrada': agua_datos['ph'],
            'agua_so4': agua_datos.get('so4', 0), 'agua_cl': agua_datos.get('cl', 0),
            'agua_objetivo': self.combo_agua_obj.get() or '',
            'equipo': self.combo_equipo.get() or '',
            'tiempo_hervor': tiempo_hervor,
            'ratio_maceracion': ratio, 'absorcion': absorcion,
            'altitud_name': self.combo_altitud.get() or DEF_ALTITUD,
        }
        if self.receta_actual_id:
            if self.db.update_recipe(self.receta_actual_id, receta_data):
                mb.showinfo("Éxito", "Receta actualizada correctamente.")
                self.cargar_lista_recetas()
                self._compartir_si_corresponde(self.receta_actual_id)
            else:
                mb.showerror("Error", f"No se pudo actualizar. ¿Existe otra receta con el nombre '{nombre}'?")
        else:
            nuevo_id = self.db.save_recipe(receta_data)
            if nuevo_id:
                mb.showinfo("Éxito", "Receta guardada.")
                self.cargar_lista_recetas()
                self._compartir_si_corresponde(nuevo_id)
                self.nueva_receta()
            else:
                mb.showerror("Error", "Nombre duplicado. Prueba con otro nombre.")

    def _compartir_si_corresponde(self, recipe_id):
        if getattr(self, "var_compartir_comunidad", None) and self.var_compartir_comunidad.get():
            threading.Thread(target=self.compartir_receta_comunidad, args=(recipe_id,), daemon=True).start()

    def eliminar_receta(self):
        if not self.receta_actual_id:
            mb.showwarning("Atención", "Selecciona una receta de la lista para eliminar."); return
        nombre = self.entry_nombre.get().strip()
        if mb.askyesno("Confirmar Eliminación", f"¿Seguro que quieres eliminar la receta '{nombre}'?"):
            self.db.delete_recipe(self.receta_actual_id)
            mb.showinfo("Eliminada", "La receta ha sido eliminada.")
            self.nueva_receta(); self.cargar_lista_recetas()

    # ==========================================
    # IMPORTACIÓN / EXPORTACIÓN
    # ==========================================
    def cargar_recetas_iniciales(self):
        if len(self.db.get_all_recipes_summary()) > 0: return
        json_path = resource_path('recetas_base.json')
        if not os.path.exists(json_path): return
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                recetas_json = json.load(f)
            for nombre, datos in recetas_json.items():
                self._guardar_desde_json(nombre, datos)
        except Exception as e:
            print(f"Error cargando JSON inicial: {e}")

    def importar_json_ui(self):
        filepath = filedialog.askopenfilename(title="Seleccionar JSON", filetypes=[("JSON", "*.json")])
        if not filepath: return
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                recetas_json = json.load(f)
            importadas, omitidas = 0, 0
            for nombre, datos in recetas_json.items():
                if self._guardar_desde_json(nombre, datos):
                    importadas += 1
                else:
                    omitidas += 1
            self.cargar_lista_recetas()
            mb.showinfo("Éxito", f"Importadas: {importadas}\nOmitidas (duplicadas): {omitidas}")
        except Exception as e:
            mb.showerror("Error", f"No se pudo leer el JSON:\n{e}")

    def _descargar_y_fusionar(self):
        """Descarga el recetario más reciente y lo fusiona. Devuelve (agregadas, omitidas)."""
        with urllib.request.urlopen(RECETARIO_URL, timeout=20) as r:
            recetas_json = json.load(r)
        refrescables = self._recetas_refrescables(recetas_json)
        agregadas, actualizadas, omitidas = 0, 0, 0
        for nombre, datos in recetas_json.items():
            h = _huella(datos)
            if self.db.recipe_exists(nombre):
                # Solo se reescribe si el contenido del recetario cambió desde la última vez
                if (nombre in refrescables and refrescables[nombre] != h
                        and self._guardar_desde_json(nombre, datos, refrescar=True)):
                    actualizadas += 1
                    refrescables[nombre] = h
                else:
                    omitidas += 1
            elif self._guardar_desde_json(nombre, datos):
                agregadas += 1
                refrescables[nombre] = h
        self._guardar_refrescables(refrescables)
        return agregadas, omitidas, actualizadas

    def actualizar_recetas_web(self):
        """Botón manual: busca y fusiona el recetario, mostrando el resultado."""
        try:
            agregadas, omitidas, actualizadas = self._descargar_y_fusionar()
            self.cargar_lista_recetas()
            mb.showinfo("Recetas actualizadas",
                        f"Nuevas recetas agregadas: {agregadas}\n"
                        f"Recetas corregidas (genéricas -> reales): {actualizadas}\n"
                        f"Sin cambios: {omitidas}\n\n"
                        "Listo, sin reinstalar nada.")
        except Exception as e:
            logger.error(f"actualizar_recetas_web: {e}")
            mb.showerror("Error",
                         "No se pudo descargar el recetario.\n\n"
                         "Revisá tu conexión y probá de nuevo.\n"
                         f"Detalle: {e}")

    def _auto_actualizar(self):
        """Al abrir la app: en segundo plano descarga y fusiona el recetario (silencioso)."""
        def tarea():
            try:
                agregadas, omitidas, actualizadas = self._descargar_y_fusionar()
                if agregadas or actualizadas:
                    self.after(0, self._refrescar_tras_auto, agregadas, actualizadas)
            except Exception as e:
                logger.error(f"_auto_actualizar: {e}")
        threading.Thread(target=tarea, daemon=True).start()

    def _refrescar_tras_auto(self, agregadas, actualizadas=0):
        self.cargar_lista_recetas()
        logger.info(f"Recetas auto-actualizadas al iniciar: {agregadas} nuevas, "
                    f"{actualizadas} corregidas.")
        try:
            self.title("Cervecera VGB - By SaintWick (recetas actualizadas)")
        except Exception:
            pass

    # ==========================================
    # COMUNIDAD — compartir/descargar recetas vía GitHub (sin backend propio)
    # ==========================================
    def _leer_token_comunidad(self):
        for var in COMUNIDAD_TOKEN_ENV:
            tok = os.environ.get(var, "").strip()
            if tok:
                return tok
        try:
            with open(COMUNIDAD_TOKEN_FILE, "r", encoding="utf-8") as f:
                tok = f.read().strip()
                if tok:
                    return tok
        except OSError:
            pass
        return None

    def _receta_a_json_recetario(self, recipe_id):
        """Convierte una receta guardada al formato del recetario (mismo formato
        que recetas_base.json / RECETARIO_URL) para compartirla."""
        r = self.db.get_full_recipe(recipe_id)
        if not r:
            return None, None
        datos = {
            "style": r.get("style", ""),
            "agua_vol": r.get("volume"),
            "fg_estimada": r.get("fg_estimated"),
            "notas": r.get("notes", ""),
            "maltas": [{"nombre": m["name"], "cantidad": m["amount"],
                        "extracto": m["extract"], "color": m["color"]} for m in r.get("maltas", [])],
            "lupulos": [{"nombre": l["name"], "cantidad": l["amount"], "aa": l["alpha_acids"],
                         "tiempo": l["time"], "formato": l.get("formato", DEF_FORMATO)}
                        for l in r.get("lupulos", [])],
            "levaduras": [{"nombre": y["name"], "atenuacion": y["attenuation"],
                           "tolerancia": y["tolerance_abv"]} for y in r.get("levaduras", [])],
        }
        return r["name"], datos

    def _slug_archivo(self, nombre):
        s = re.sub(r"[^a-zA-Z0-9]+", "-", nombre.strip().lower()).strip("-")
        return (s or "receta") + ".json"

    def compartir_receta_comunidad(self, recipe_id):
        """Sube (o actualiza) la receta como JSON en recetas_comunidad/ del repo,
        vía la API de contenidos de GitHub (sin clonar el repo). Cualquier usuario
        de la app la baja después con '🌐 Recetas de la Comunidad'. Se ejecuta en
        un hilo aparte (la llama guardar_receta), por eso los avisos van con
        self.after(0, ...) para tocar la UI desde el hilo principal."""
        token = self._leer_token_comunidad()
        if not token:
            self.after(0, lambda: mb.showwarning(
                "Compartir con la comunidad",
                "No hay credenciales de GitHub configuradas para compartir.\n\n"
                "Configuralo una sola vez con alguna de estas opciones:\n"
                f"  · echo TU_TOKEN > {COMUNIDAD_TOKEN_FILE}\n"
                "  · variable de entorno GITHUB_TOKEN\n\n"
                "La receta se guardó localmente igual; sólo no se compartió."))
            return
        nombre, datos = self._receta_a_json_recetario(recipe_id)
        if not nombre:
            return
        archivo = self._slug_archivo(nombre)
        url = COMUNIDAD_ARCHIVO_URL.format(archivo=archivo)
        contenido_b64 = base64.b64encode(
            json.dumps({nombre: datos}, ensure_ascii=False, indent=2).encode("utf-8")).decode("ascii")
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json",
                  "User-Agent": "CerveceraVGB"}
        sha = None
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as r:
                sha = json.load(r).get("sha")
        except urllib.error.HTTPError as e:
            if e.code != 404:
                logger.error(f"compartir_receta_comunidad (GET): {e}")
        except Exception as e:
            logger.error(f"compartir_receta_comunidad (GET): {e}")
        payload = {"message": f"Comunidad: comparte receta '{nombre}'", "content": contenido_b64}
        if sha:
            payload["sha"] = sha
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                         headers=headers, method="PUT")
            with urllib.request.urlopen(req, timeout=30) as r:
                json.load(r)
            self.db.mark_recipe_compartida(recipe_id)
            self.after(0, lambda: mb.showinfo("Comunidad", f"'{nombre}' se compartió con la comunidad. 🌐"))
        except Exception as e:
            msg = str(e)
            logger.error(f"compartir_receta_comunidad (PUT): {msg}")
            self.after(0, lambda msg=msg: mb.showerror("Comunidad", f"No se pudo compartir la receta.\n{msg}"))

    def descargar_recetas_comunidad(self):
        """Lista y descarga las recetas compartidas por la comunidad (lectura
        pública, sin token) y las fusiona sin pisar las locales."""
        try:
            req = urllib.request.Request(COMUNIDAD_LISTADO_URL, headers={"User-Agent": "CerveceraVGB"})
            with urllib.request.urlopen(req, timeout=20) as r:
                listado = json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return 0, 0  # todavía nadie compartió nada
            raise
        agregadas, omitidas = 0, 0
        for archivo in listado:
            if not archivo.get("name", "").endswith(".json"):
                continue
            try:
                with urllib.request.urlopen(archivo["download_url"], timeout=20) as r:
                    receta_json = json.load(r)
                for nombre, datos in receta_json.items():
                    if self._guardar_desde_json(nombre, datos):
                        agregadas += 1
                    else:
                        omitidas += 1
            except Exception as e:
                logger.error(f"descargar_recetas_comunidad ({archivo.get('name')}): {e}")
        return agregadas, omitidas

    def buscar_recetas_comunidad_ui(self):
        try:
            agregadas, omitidas = self.descargar_recetas_comunidad()
            self.cargar_lista_recetas()
            mb.showinfo("Recetas de la Comunidad",
                        f"Nuevas recetas compartidas: {agregadas}\nYa las tenías: {omitidas}")
        except Exception as e:
            logger.error(f"buscar_recetas_comunidad_ui: {e}")
            mb.showerror("Error", f"No se pudo consultar la comunidad.\n{e}")

    def comprobar_actualizaciones(self):
        """Busca una versión más nueva del PROGRAMA. En Windows la instala en silencio."""
        try:
            req = urllib.request.Request(RELEASE_API_URL,
                                         headers={'User-Agent': 'CerveceraVGB'})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.load(r)
            tag = data.get('tag_name', '')
            version = tag.lstrip('v')
            if version == APP_VERSION:
                mb.showinfo("Actualización", f"Tenés la versión {APP_VERSION}. ¡Estás al día! ✅")
                return
            # elegir el instalador de esta plataforma
            url = None
            for a in data.get('assets', []):
                n = a['name']
                if sys.platform == 'win32' and n.lower().endswith('.exe'):
                    url = a['browser_download_url']; break
                elif sys.platform == 'darwin' and 'macos-arm64' in n:
                    url = a['browser_download_url']; break
                elif sys.platform.startswith('linux') and n.endswith('.AppImage'):
                    url = a['browser_download_url']; break
            if not url:
                mb.showinfo("Actualización", f"Hay una versión nueva: {version}.\nDescargala del release.")
                return
            destino = os.path.join(tempfile.gettempdir(), os.path.basename(url))
            logger.info(f"Descargando actualización {version} -> {destino}")
            with urllib.request.urlopen(url, timeout=180) as r, open(destino, 'wb') as f:
                f.write(r.read())
            if sys.platform == 'win32':
                logger.info("Lanzando instalador en silencio (auto-update).")
                subprocess.Popen([destino, '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'])
                mb.showinfo("Actualización",
                            "Se descargó la versión nueva y se está instalando.\nLa app se cerrará; volvé a abrirla al terminar.")
                self.after(1500, lambda: os._exit(0))
            else:
                if sys.platform == 'darwin':
                    subprocess.Popen(['open', destino])
                else:
                    subprocess.Popen(['xdg-open', destino])
                mb.showinfo("Actualización",
                            f"Se descargó la versión {version}.\n\n{os.path.basename(destino)}\n"
                            "Se abrió para que la instales (en Linux/macOS instalar requiere permisos de administrador).")
        except Exception as e:
            logger.error(f"comprobar_actualizaciones: {e}")
            mb.showerror("Error", f"No se pudo comprobar actualizaciones.\n{e}")

    def _guardar_desde_json(self, nombre, datos, refrescar=False):
        """Adapta una receta del JSON (formato móvil) y la guarda.
        Si ya existe la actualiza SOLO si viene del recetario oficial (refrescar=True);
        así se corrigen las recetas genéricas viejas sin tocar las del usuario."""
        existe = self.db.recipe_exists(nombre)
        if existe and not refrescar:
            return None
        # Levadura: la de la receta importada si la trae; si no, la de por defecto
        levs = datos.get('levaduras') or []
        if levs:
            levadura_nombre = levs[0].get('nombre') or DEF_LEVADURA
            levadura_datos = {"atenuacion": float(levs[0].get('atenuacion') or 81.0),
                              "tolerancia_abv": float(levs[0].get('tolerancia') or 12.0)}
        else:
            levadura_nombre = DEF_LEVADURA
            levadura_datos = LEVADURAS_AR.get(levadura_nombre, {"atenuacion": 81.0, "tolerancia_abv": 12.0})
        receta = {
            'name': nombre, 'style': datos.get('style', 'Estilo Base'),
            'volume': datos.get('agua_vol', 20), 'efficiency': 0.75,
            'og_estimated': None, 'fg_estimated': datos.get('fg_estimada', 1.010),
            'ibu_estimated': None, 'srm_estimated': None,
            'notes': datos.get('notas', ''),
            'maltas': [{'nombre': m['nombre'], 'cantidad': m['cantidad'],
                        'extracto': m.get('extracto', 300), 'color': m.get('color', 2)}
                       for m in datos.get('maltas', [])],
            'lupulos': [{'nombre': l['nombre'], 'cantidad': l['cantidad'],
                         'aa': l.get('aa', 5), 'tiempo': l.get('tiempo', 60),
                         'formato': l.get('formato', DEF_FORMATO)}
                        for l in datos.get('lupulos', [])],
            'levaduras': [{'nombre': levadura_nombre,
                           'atenuacion': levadura_datos['atenuacion'],
                           'tolerancia': levadura_datos['tolerancia_abv']}],
        }
        if existe:
            rid = self._id_receta(nombre)
            return self.db.update_recipe(rid, receta) if rid else None
        return self.db.save_recipe(receta)

    def _id_receta(self, nombre):
        """Id de una receta guardada, buscándola por nombre."""
        try:
            for r in self.db.get_all_recipes_summary():
                if r['name'] == nombre:
                    return r['id']
        except Exception as e:
            logger.error(f"_id_receta({nombre}): {e}")
        return None

    def _recetas_refrescables(self, recetas_json):
        """Nombres que la app puede refrescar desde el recetario.
        La primera vez son los que ya existen y figuran en el recetario: esas son
        justamente las recetas genéricas viejas que hay que corregir."""
        guardado = self.db.get_setting('recetas_refrescables', None)
        if guardado is not None:
            try:
                datos = json.loads(guardado)
                if isinstance(datos, list):        # formato anterior (solo nombres)
                    return {n: None for n in datos}
                return dict(datos)
            except Exception:
                return {}
        try:
            existentes = {r['name'] for r in self.db.get_all_recipes_summary()}
        except Exception:
            existentes = set()
        # Primera vez: los que ya existen y figuran en el recetario son los genéricos viejos
        return {n: None for n in recetas_json if n in existentes}

    def _guardar_refrescables(self, nombres):
        try:
            self.db.set_setting('recetas_refrescables', json.dumps(nombres, ensure_ascii=False))
        except Exception as e:
            logger.error(f"_guardar_refrescables: {e}")

    def _recolectar_datos_exportacion(self):
        resultados = self.calcular_y_mostrar()
        if not resultados: return None
        maltas, lupulos = self.leer_ingredientes_ui()
        volumen, eficiencia, _, _, _, _ = self._leer_parametros()
        r = resultados['r']
        return {
            'name': self.entry_nombre.get().strip() or "Sin Nombre",
            'style': self.combo_estilo_bjcp.get(),
            'volume': volumen,
            'efficiency': eficiencia,
            'og': r['og'], 'fg': r['fg'], 'abv': r['abv'],
            'ibu': r['ibu'], 'srm': r['srm'],
            'ph': r['ph'], 'ph_hervor': r['ph_hervor'], 'ph_final': r['ph_final'],
            'maltas': maltas, 'lupulos': lupulos,
            'notes': self.texto_notas.get("1.0", "end-1c").strip(),
        }

    def exportar_pdf_ui(self):
        data = self._recolectar_datos_exportacion()
        if not data: return
        filepath = filedialog.asksaveasfilename(defaultextension=".pdf",
                                                filetypes=[("PDF", "*.pdf")],
                                                title="Guardar PDF", initialfile=data['name'])
        if not filepath: return
        if exportar_pdf(data, filepath):
            mb.showinfo("Éxito", f"PDF guardado en:\n{filepath}")
        else:
            mb.showerror("Error", "No se pudo generar el PDF.")

    def exportar_xml_ui(self):
        data = self._recolectar_datos_exportacion()
        if not data: return
        filepath = filedialog.asksaveasfilename(defaultextension=".xml",
                                                filetypes=[("BeerXML", "*.xml")],
                                                title="Guardar BeerXML", initialfile=data['name'])
        if not filepath: return
        if exportar_beerxml(data, filepath):
            mb.showinfo("Éxito", f"BeerXML guardado en:\n{filepath}")
        else:
            mb.showerror("Error", "No se pudo generar el BeerXML.")

    def abrir_menu_acciones(self):
        """Despliega/oculta un dropdown propio bajo el botón Menú (se cierra al elegir
        una opción o al perder el foco; no queda pegado como el tk.Menu nativo)."""
        if self._menu_popup is not None and self._menu_popup.winfo_exists():
            self._cerrar_menu_acciones()
            return
        x = self.btn_menu.winfo_rootx()
        y = self.btn_menu.winfo_rooty() + self.btn_menu.winfo_height() + 2
        popup = ctk.CTkToplevel(self)
        popup.overrideredirect(True)
        popup.geometry(f"+{x}+{y}")
        popup.attributes("-topmost", True)
        frame = ctk.CTkFrame(popup, fg_color="#2c2c2c", corner_radius=6, border_width=1,
                             border_color="#475569")
        frame.pack(fill="both", expand=True)
        opciones = (
            ("📂 Importar JSON", self.importar_json_ui),
            ("🔄 Buscar recetas nuevas", self.actualizar_recetas_web),
            ("🌐 Recetas de la Comunidad", self.buscar_recetas_comunidad_ui),
            ("⬆️ Comprobar actualizaciones", self.comprobar_actualizaciones),
            ("💾 Exportar PDF", self.exportar_pdf_ui),
            ("💾 Exportar BeerXML", self.exportar_xml_ui),
        )
        for texto, accion in opciones:
            ctk.CTkButton(frame, text=texto, anchor="w", fg_color="transparent",
                         hover_color="#374151", height=30,
                         command=lambda a=accion: self._ejecutar_accion_menu(a)
                         ).pack(fill="x", padx=4, pady=2)
        popup.bind("<FocusOut>", lambda e: self._cerrar_menu_acciones())
        self._menu_popup = popup
        popup.after(10, popup.focus_force)

    def _ejecutar_accion_menu(self, accion):
        self._cerrar_menu_acciones()
        accion()

    def _cerrar_menu_acciones(self):
        if self._menu_popup is not None:
            try:
                self._menu_popup.destroy()
            except Exception:
                pass
            self._menu_popup = None

    def toggle_lista_recetas(self):
        """Muestra u oculta la lista de recetas al presionar 'Mis Recetas'."""
        if self._recetas_visibles:
            self.lista_recetas.grid_remove()
            self.btn_toggle_recetas.configure(text="🍺 Mis Recetas  ▸")
        else:
            self.lista_recetas.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
            self.btn_toggle_recetas.configure(text="🍺 Mis Recetas  ▾")
        self._recetas_visibles = not self._recetas_visibles

    def mostrar_ayuda(self):
        AyudaDialog(self)

    def mostrar_log(self):
        """Muestra la ruta del registro y lo abre en el visor por defecto."""
        logp = os.path.join(get_data_dir(), "cervecera_debug.log")
        existe = os.path.exists(logp)
        try:
            if existe:
                if sys.platform == "win32":
                    os.startfile(logp)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", logp])
                else:
                    subprocess.Popen(["xdg-open", logp])
        except Exception as e:
            print(f"No se pudo abrir el log: {e}")
        if existe:
            mb.showinfo("Registro (log)", f"El registro de la app está en:\n\n{logp}\n\nSe abrió en el visor por defecto.")
        else:
            mb.showinfo("Registro (log)", "Todavía no hay registro de errores.\n\nSi la app falla, aparecerá acá.")
