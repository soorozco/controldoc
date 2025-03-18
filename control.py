import re
import io
import streamlit as st
import pandas as pd
import json
from sqlalchemy import create_engine, Table, Column, Integer, String, Text, MetaData, insert, delete, update, select
import matplotlib.pyplot as plt
from st_aggrid import AgGrid, GridOptionsBuilder
from st_aggrid.shared import GridUpdateMode
from datetime import datetime
import altair as alt
from st_aggrid.shared import GridUpdateMode
from st_aggrid import AgGrid, GridOptionsBuilder

# Configuración de la base de datos mejorada
def setup_database():
    engine = create_engine('sqlite:///control_documental.db')
    metadata = MetaData()
    
    # Tabla de documentos
    documentos = Table('documentos', metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('codigo', String, unique=True),
        Column('nombre_documento', String),
        Column('version', String),
        Column('fecha_emision', String),
        Column('fecha_revision', String),
        Column('objetivo', Text),
        Column('alcance', Text),
        Column('responsable_actualizacion', String),
        Column('responsable_ejecucion', String),
        Column('responsable_supervision', String),
        Column('pasos', Text),
        Column('historial_cambios', Text),
        Column('riesgos', Text),
        Column('barreras_seguridad', Text),
        Column('documentos_referencia', Text),
        Column('autorizaciones', Text),
        Column('estado', String, default="Borrador"),
        Column('comentarios_revision', Text, default="")
    )
    
    # Tabla de registros
    registros = Table('registros', metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('codigo', String, unique=True),
        Column('nombre_registro', String),
        Column('version', String),
        Column('documento_origen', String),
        Column('responsable_recoleccion', String),
        Column('medio_almacenamiento', String),
        Column('tiempo_retencion', String),
        Column('disposicion_final', String),
        Column('estado', String, default="Activo")
    )
    
    # Tabla de personal autorizado
    personal = Table('personal', metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('nombre_completo', String, unique=True),
        Column('puesto', String),
        Column('area', String),
        Column('correo', String),
        Column('activo', Integer, default=1)
    )
    
    # Tabla de cambios de estado
    cambios_estado = Table('cambios_estado', metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('documento_codigo', String),
        Column('estado_anterior', String),
        Column('nuevo_estado', String),
        Column('comentarios', Text),
        Column('fecha_cambio', String)
    )
    
    metadata.create_all(engine)
    return engine, documentos, registros, personal, cambios_estado
    
# Inicialización de la base de datos mejorada (sin indentación)
engine, documentos, registros, personal, cambios_estado = setup_database()

# Configuración de la aplicación Streamlit
st.set_page_config(page_title="Sistema Integrado ISO 9001:2015", layout="wide")
st.title("📋 Sistema de Gestión Documental y Registros ISO 9001:2015")

# Configuración de las pestañas con el nuevo orden y nombres actualizados
tabs = st.tabs([
    "Subir JSON", 
    "Control de Documentos", 
    "Control de Registros", 
    "Documentos", 
    "Personal Autorizado", 
    "Ciclo Documental", 
    "Dashboard"
])

# Funciones para cargar datos con caché
@st.cache_data
def cargar_datos():
    try:
        with engine.connect() as conn:
            return pd.read_sql("SELECT * FROM documentos", conn)
    except Exception as e:
        st.error(f"Error al cargar los datos de documentos: {e}")
        return pd.DataFrame()

@st.cache_data
def cargar_registros():
    try:
        with engine.connect() as conn:
            return pd.read_sql("SELECT * FROM registros", conn)
    except Exception as e:
        st.error(f"Error al cargar los datos de registros: {e}")
        return pd.DataFrame()

@st.cache_data
def cargar_personal():
    try:
        with engine.connect() as conn:
            return pd.read_sql("SELECT * FROM personal", conn)
    except Exception as e:
        st.error(f"Error al cargar los datos de personal: {e}")
        return pd.DataFrame()

# Función para extraer formatos mencionados en los pasos del procedimiento
def extraer_formatos(pasos_json):
    formatos = []
    try:
        pasos = json.loads(pasos_json) if pasos_json else []
        patron = r'F-\d{3}'  # Patrón para buscar formatos tipo F-001, F-123, etc.
        
        for paso in pasos:
            descripcion = paso.get('Descripción', '')
            encontrados = re.findall(patron, descripcion)
            formatos.extend(encontrados)
        
        # Eliminar duplicados y ordenar
        return sorted(list(set(formatos)))
    except Exception as e:
        st.error(f"Error al extraer formatos: {e}")
        return []

# Función para extraer roles de los pasos
def extraer_roles(pasos_json):
    roles = []
    try:
        pasos = json.loads(pasos_json) if pasos_json else []
        
        for paso in pasos:
            responsable = paso.get('Responsable', '')
            if responsable and responsable not in roles:
                roles.append(responsable)
        
        return roles
    except Exception as e:
        st.error(f"Error al extraer roles: {e}")
        return []

# Función para cargar contenido JSON
def load_json_content(uploaded_json):
    try:
        json_content = json.load(uploaded_json)
        return json_content
    except json.JSONDecodeError as e:
        st.error(f"Error al decodificar el archivo JSON: {e}")
        return None
    except Exception as e:
        st.error(f"Error inesperado al leer el archivo JSON: {e}")
        return None
    
# Cargar datos
df = cargar_datos()
df_registros = cargar_registros()
df_personal = cargar_personal()

# Tab 1: Subir JSON
with tabs[0]:
    st.header("Subir archivo JSON y extraer datos")
    uploaded_json = st.file_uploader("Selecciona un archivo JSON", type=["json"], key="json_upload")
    
    if uploaded_json is not None:
        json_content = load_json_content(uploaded_json)
        if json_content:
            st.success("Contenido del archivo JSON cargado correctamente.")
            st.json(json_content)
            
            # Extraer datos del JSON como antes
            registro_json = {
                "codigo": json_content.get("Código", ""),
                "nombre_documento": json_content.get("Nombre del Documento", ""),
                "version": json_content.get("Versión vigente", ""),
                "fecha_emision": json_content.get("Fecha de emisión", ""),
                "fecha_revision": json_content.get("Fecha de revisión", ""),
                "objetivo": json_content.get("Objetivo", ""),
                "alcance": json_content.get("Alcance", ""),
                "responsable_actualizacion": json_content.get("Responsabilidades", {}).get("Actualización", ""),
                "responsable_ejecucion": "",  # Se completará después de procesar los pasos
                "responsable_supervision": json_content.get("Responsabilidades", {}).get("Supervisión", ""),
                "pasos": json.dumps(json_content.get("Desarrollo del Proceso", {}).get("table", []), ensure_ascii=False),
                "historial_cambios": json.dumps(json_content.get("Control de Cambios", {}).get("table", []), ensure_ascii=False),
                "riesgos": json.dumps(json_content.get("Gestión de Riesgos", {}).get("Ponderación de riesgos", []), ensure_ascii=False),
                "barreras_seguridad": json.dumps(json_content.get("Gestión de Riesgos", {}).get("Barreras de seguridad", []), ensure_ascii=False),
                "documentos_referencia": json.dumps(json_content.get("Documentos de Referencia", {}).get("table", []), ensure_ascii=False),
                "autorizaciones": json.dumps(json_content.get("Autorizaciones", {}).get("table", []), ensure_ascii=False),
                "estado": "Borrador",
                "comentarios_revision": ""
            }
            
            # Extraer roles de los pasos y completar responsable_ejecucion
            pasos_str = registro_json["pasos"]
            roles = extraer_roles(pasos_str)
            registro_json["responsable_ejecucion"] = ", ".join(roles)
            
            # Insertar personal de las autorizaciones en la tabla de personal
            try:
                autorizaciones = json.loads(registro_json["autorizaciones"])
                personal_registrar = []
                
                for auth in autorizaciones:
                    nombre = auth.get("Nombre", "")
                    puesto = auth.get("Puesto", "")
                    if nombre and puesto:
                        personal_registrar.append({
                            "nombre_completo": nombre,
                            "puesto": puesto,
                            "area": "",  # Se puede completar manualmente después
                            "correo": "",  # Se puede completar manualmente después
                            "activo": 1
                        })
                
                # Insertar en tabla de personal si no existen ya
                if personal_registrar:
                    with engine.connect() as conn:
                        for persona in personal_registrar:
                            existing = conn.execute(
                                select(personal).where(personal.c.nombre_completo == persona["nombre_completo"])
                            ).fetchone()
                            
                            if not existing:
                                conn.execute(insert(personal), persona)
                        conn.commit()
            except Exception as e:
                st.warning(f"Error al procesar personal de autorizaciones: {str(e)}")
            
            # Extraer formatos mencionados en los pasos
            formatos = extraer_formatos(pasos_str)
            
            # Verificar si el documento ya existe
            with engine.connect() as conn:
                existing = pd.read_sql(f"SELECT * FROM documentos WHERE codigo = '{registro_json['codigo']}'", conn)
                if existing.empty:
                    conn.execute(insert(documentos), registro_json)
                    conn.commit()
                    st.success("Datos extraídos e insertados en la base de datos con estado inicial Borrador.")
                    
                    # Mostrar formatos detectados y opción para registrarlos
                    if formatos:
                        st.subheader("Formatos detectados en el procedimiento")
                        for formato in formatos:
                            st.info(f"Formato detectado: {formato}")
                        
                        st.warning("Los formatos detectados pueden ser registrados en la pestaña 'Control de Registros'")
                else:
                    st.warning("El documento ya existe en la base de datos.")
            st.cache_data.clear()

    # Botón para actualizar el Control de Documentos
    if st.button("🔄 Actualizar Control de Documentos"):
        st.cache_data.clear()  # Limpiar la caché para recargar los datos
        st.success("Control de Documentos actualizado correctamente.")

# Tab 2: Control de Documentos
with tabs[1]:
    st.header("📂 Control de Documentos")
    
    # Verificar si hay documentos registrados
    if not df.empty:
        # Preparar los datos para la tabla
        df["tipo_documento"] = df["codigo"].apply(lambda x: "Procedimiento" if x.startswith("PR") else "Otro")
        df["fecha_vigencia"] = df["fecha_revision"]  # Fecha de vigencia es igual a la fecha de revisión
        df["elaboro"] = df["responsable_actualizacion"]
        df["reviso"] = df["responsable_supervision"]
        df["autorizo"] = df["responsable_ejecucion"]

        # Seleccionar las columnas a mostrar
        columnas_mostrar = [
            "codigo", 
            "nombre_documento", 
            "tipo_documento", 
            "version", 
            "fecha_emision", 
            "fecha_vigencia", 
            "elaboro", 
            "reviso", 
            "autorizo"
        ]
        df_tabla = df[columnas_mostrar]

        # Mostrar la tabla con AgGrid
        st.subheader("📋 Documentos Registrados")
        gb = GridOptionsBuilder.from_dataframe(df_tabla)
        gb.configure_pagination(paginationPageSize=10)
        gb.configure_default_column(filterable=True, sortable=True)
        grid_options = gb.build()

        AgGrid(
            df_tabla,
            gridOptions=grid_options,
            height=400,
            theme="streamlit",
            fit_columns_on_grid_load=True
        )
    else:
        st.info("📭 No hay documentos registrados. Suba un documento en la pestaña 1 para comenzar.")

# Tab 3: Control de Registros
with tabs[2]:
    st.header("📁 Control de Registros")
    
    # Cargar registros con manejo de DataFrame vacío
    registros_df = cargar_registros()
    
    # --- Sección para agregar nuevos registros ---
    with st.expander("➕ Agregar Nuevo Registro", expanded=False):
        with st.form("nuevo_registro_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                codigo = st.text_input("Código (Formato F-XXX):", help="Ejemplo: F-001")
                nombre_registro = st.text_input("Nombre del Registro:")
                version = st.text_input("Versión:", value="1.0")
            with col2:
                # Obtener documentos existentes de manera segura
                doc_options = [""] + df["codigo"].tolist() if not df.empty else [""]
                documento_origen = st.selectbox("Documento Origen:", options=doc_options)
                responsable_recoleccion = st.text_input("Responsable de Recolección:")
            
            medio_almacenamiento = st.selectbox(
                "Medio de Almacenamiento:",
                ["", "Físico", "Digital", "Híbrido"],
                index=0
            )
            
            tiempo_retencion = st.text_input("Tiempo de Retención:", placeholder="Ej: 2 años")
            disposicion_final = st.selectbox(
                "Disposición Final:",
                ["", "Archivado", "Destrucción", "Conservación permanente"],
                index=0
            )
            
            if st.form_submit_button("Registrar Formato", type="primary"):
                if not codigo or not nombre_registro:
                    st.error("❌ Campos obligatorios: Código y Nombre del Registro")
                else:
                    try:
                        # Verificar existencia usando SQLAlchemy Core
                        with engine.connect() as conn:
                            existing = conn.execute()
                            select(registros).where(registros.c.codigo == codigo)
                            fetchone()
                            
                        if existing:
                            st.warning(f"⚠️ El código {codigo} ya está registrado")
                        else:
                            nuevo_registro = {
                                "codigo": codigo,
                                "nombre_registro": nombre_registro,
                                "version": version,
                                "documento_origen": documento_origen,
                                "responsable_recoleccion": responsable_recoleccion,
                                "medio_almacenamiento": medio_almacenamiento,
                                "tiempo_retencion": tiempo_retencion,
                                "disposicion_final": disposicion_final,
                                "estado": "Activo"
                            }
                            
                            with engine.connect() as conn:
                                conn.execute(insert(registros), nuevo_registro)
                                conn.commit()
                            
                            st.success(f"✅ Registro {codigo} creado exitosamente")
                            st.cache_data.clear()
                            
                    except Exception as e:
                        st.error(f"🚨 Error crítico: {str(e)}")

    # --- Sección de visualización y filtrado ---
    st.subheader("Registros Existentes")
    
    if not registros_df.empty:
        # Mostrar tabla con AgGrid para mejor interactividad
        gb = GridOptionsBuilder.from_dataframe(registros_df)
        gb.configure_pagination(enabled=True)
        gb.configure_default_column(filterable=True, sortable=True)
        grid_options = gb.build()
        
        AgGrid(
            registros_df,
            gridOptions=grid_options,
            height=300,
            theme="streamlit",
            fit_columns_on_grid_load=True
        )
        
        # --- Filtrado por documento origen ---
        st.subheader("Filtrado Avanzado")
        col_filtro1, col_filtro2 = st.columns(2)
        with col_filtro1:
            doc_filtro = st.selectbox(
                "Filtrar por Documento Origen:",
                options=["Todos"] + registros_df["documento_origen"].unique().tolist()
            )
        
        with col_filtro2:
            estado_filtro = st.selectbox(
                "Filtrar por Estado:",
                options=["Todos"] + registros_df["estado"].unique().tolist()
            )
        
        # Aplicar filtros
        filtered_df = registros_df.copy()
        if doc_filtro != "Todos":
            filtered_df = filtered_df[filtered_df["documento_origen"] == doc_filtro]
        if estado_filtro != "Todos":
            filtered_df = filtered_df[filtered_df["estado"] == estado_filtro]
            
        st.metric("Registros Filtrados", len(filtered_df))
        
    else:
        st.info("📭 No hay registros disponibles. Crea uno usando el formulario superior")

    # --- Sección de eliminación segura ---
    with st.expander("🗑️ Eliminar Registro", expanded=False):
        if not registros_df.empty:
            registro_a_eliminar = st.selectbox(
                "Seleccione registro a eliminar:",
                registros_df["codigo"],
                key="delete_registro"
            )
            
            if st.button("Confirmar Eliminación", key="confirm_delete_reg"):
                try:
                    with engine.connect() as conn:
                        with conn.begin():
                            conn.execute(
                                delete(registros)
                                .where(registros.c.codigo == registro_a_eliminar)
                            )
                    st.success(f"✅ Registro {registro_a_eliminar} eliminado")
                    st.cache_data.clear()
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"🚨 Error al eliminar: {str(e)}")
        else:
            st.warning("No hay registros para eliminar")

# Tab 4: Documentos
with tabs[3]:
    st.header("📝 Documentos")
    
    # Verificar si hay documentos registrados
    if not df.empty:
        documento_seleccionado = st.selectbox(
            "Seleccione un documento:",
            df["codigo"],
            key="doc_detalles"
        )
        detalles = df[df["codigo"] == documento_seleccionado].iloc[0]

        # Mostrar información en el orden solicitado
        st.subheader("📄 Información del Documento")
        st.write(f"*Nombre del Documento:* {detalles['nombre_documento']}")
        st.write(f"*Código:* {detalles['codigo']}")
        st.write(f"*Versión Vigente:* {detalles['version']}")
        st.write(f"*Fecha de Emisión:* {detalles['fecha_emision']}")
        st.write(f"*Fecha de Revisión:* {detalles['fecha_revision']}")
        st.write(f"*Objetivo:* {detalles['objetivo']}")
        st.write(f"*Alcance:* {detalles['alcance']}")

        # Responsabilidades
        st.subheader("👥 Responsabilidades")
        st.write(f"*Actualización:* {detalles['responsable_actualizacion']}")
        st.write(f"*Ejecución:* {detalles['responsable_ejecucion']}")
        st.write(f"*Supervisión:* {detalles['responsable_supervision']}")

        # Desarrollo del Proceso
        st.subheader("📋 Desarrollo del Proceso")
        try:
            pasos = json.loads(detalles["pasos"]) if detalles["pasos"] else []
            if pasos:
                # Crear un DataFrame para los pasos
                df_pasos = pd.DataFrame(pasos)

                # Configurar AgGrid para ajustar el alto de las filas
                gb = GridOptionsBuilder.from_dataframe(df_pasos)
                gb.configure_default_column(wrapText=True, autoHeight=True)  # Ajustar texto y alto
                grid_options = gb.build()

                # Mostrar la tabla con AgGrid
                AgGrid(
                    df_pasos,
                    gridOptions=grid_options,
                    height=300,
                    fit_columns_on_grid_load=True,
                    theme="streamlit"
                )
            else:
                st.info("No se han registrado pasos para este documento.")
        except Exception as e:
            st.error(f"Error al cargar los pasos: {str(e)}")

        # Gestión de Riesgos
        st.subheader("⚠️ Gestión de Riesgos")
        try:
            # Convertir los datos de riesgos y barreras de seguridad en listas
            riesgos = json.loads(detalles["riesgos"]) if detalles["riesgos"] else []
            barreras = json.loads(detalles["barreras_seguridad"]) if detalles["barreras_seguridad"] else []

            if riesgos or barreras:
                # Asegurar que ambas listas tengan el mismo tamaño
                max_len = max(len(riesgos), len(barreras))
                riesgos.extend([""] * (max_len - len(riesgos)))
                barreras.extend([""] * (max_len - len(barreras)))

                # Crear el DataFrame
                df_riesgos = pd.DataFrame({
                    "Ponderación de riesgos": riesgos,
                    "Barreras de seguridad": barreras
                })

                # Configurar AgGrid para ajustar el alto de las filas
                gb = GridOptionsBuilder.from_dataframe(df_riesgos)
                gb.configure_default_column(wrapText=True, autoHeight=True)  # Ajustar texto y alto
                grid_options = gb.build()

                # Mostrar la tabla con AgGrid
                AgGrid(
                    df_riesgos,
                    gridOptions=grid_options,
                    height=300,
                    fit_columns_on_grid_load=True,
                    theme="streamlit"
                )
            else:
                st.info("No se han registrado riesgos ni barreras de seguridad.")
        except Exception as e:
            st.error(f"Error al cargar la gestión de riesgos: {str(e)}")
        # Documentos de Referencia
        st.subheader("📚 Documentos de Referencia")
        try:
            documentos_referencia = json.loads(detalles["documentos_referencia"]) if detalles["documentos_referencia"] else []
            if documentos_referencia:
                df_referencia = pd.DataFrame(documentos_referencia)
                st.dataframe(df_referencia, use_container_width=True)
            else:
                st.info("No se han registrado documentos de referencia.")
        except Exception as e:
            st.error(f"Error al cargar los documentos de referencia: {str(e)}")

        # Control de Cambios
        st.subheader("🔄 Control de Cambios")
        try:
            cambios = json.loads(detalles["historial_cambios"]) if detalles["historial_cambios"] else []
            if cambios:
                df_cambios = pd.DataFrame(cambios)
                st.dataframe(df_cambios, use_container_width=True)
            else:
                st.info("No se han registrado cambios para este documento.")
        except Exception as e:
            st.error(f"Error al cargar el control de cambios: {str(e)}")

        # Autorizaciones
        st.subheader("🖋️ Autorizaciones")
        try:
            autorizaciones = json.loads(detalles["autorizaciones"]) if detalles["autorizaciones"] else []

            if autorizaciones and len(autorizaciones) == 2:
                # Extraer nombres y cargos de las autorizaciones
                nombres = autorizaciones[0]
                cargos = autorizaciones[1]

                # Crear la estructura de la tabla con el formato solicitado (sin la columna vacía)
                data_autorizaciones = [
                    {"Rol": "Elaboró", "Nombre": nombres.get("Elaboró", ""), "Cargo": cargos.get("Cargo Elaboró", "")},
                    {"Rol": "Revisó", "Nombre": nombres.get("Revisó", ""), "Cargo": cargos.get("Cargo Revisó", "")},
                    {"Rol": "Autorizó", "Nombre": nombres.get("Autorizó", ""), "Cargo": cargos.get("Cargo Autorizó", "")}
                ]

                # Convertir a DataFrame
                df_autorizaciones = pd.DataFrame(data_autorizaciones)

                # Mostrar la tabla con el formato solicitado
                st.dataframe(df_autorizaciones, use_container_width=True)
            else:
                st.info("No se han registrado autorizaciones o el formato es incorrecto.")
        except Exception as e:
            st.error(f"Error al cargar las autorizaciones: {str(e)}")

    else:
        st.info("📭 No hay documentos disponibles. Suba un documento en la pestaña 1 para comenzar.")

# Tab 5: Personal Autorizado
with tabs[4]:
    st.header("👥 Gestión de Personal Autorizado")
    
    # Cargar personal con manejo de errores
    try:
        personal_df = cargar_personal()
    except Exception as e:
        st.error(f"Error al cargar personal: {str(e)}")
        personal_df = pd.DataFrame()

    # --- Formulario de Registro ---
    with st.expander("➕ Registrar Nuevo Personal", expanded=False):
        with st.form("nuevo_personal_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nombre_completo = st.text_input("Nombre Completo*")
                puesto = st.text_input("Puesto*")
            with col2:
                area = st.text_input("Área/Departamento")
                correo = st.text_input("Correo Electrónico")
            
            activo = st.toggle("Activo", value=True)
            
            if st.form_submit_button("Guardar Personal", type="primary"):
                # Validar que los campos obligatorios no estén vacíos
                if not nombre_completo.strip() or not puesto.strip():
                    st.error("❌ Los campos 'Nombre Completo' y 'Puesto' son obligatorios.")
                else:
                    try:
                        # Verificar si el personal ya existe en la base de datos
                        with engine.connect() as conn:
                            existente = conn.execute(
                                select(personal).where(personal.c.nombre_completo == nombre_completo.strip())
                            ).fetchone()
                            
                            if existente:
                                st.warning(f"⚠️ El personal '{nombre_completo}' ya está registrado.")
                            else:
                                # Insertar el nuevo registro en la base de datos
                                nuevo_personal = {
                                    "nombre_completo": nombre_completo.strip(),
                                    "puesto": puesto.strip(),
                                    "area": area.strip(),
                                    "correo": correo.strip().lower(),
                                    "activo": 1 if activo else 0
                                }
                                
                                conn.execute(insert(personal), nuevo_personal)
                                conn.commit()
                                
                                st.success("✅ Personal registrado exitosamente.")
                                st.cache_data.clear()  # Limpiar la caché
                                # Recargar los datos manualmente
                                personal_df = cargar_personal()
                    except Exception as e:
                        st.error(f"🚨 Error al guardar en la base de datos: {str(e)}")

    # --- Listado y Gestión ---
    st.subheader("Listado de Personal")

    if not personal_df.empty:
        # Preprocesar los datos para que sean compatibles con AgGrid
        personal_df = personal_df.astype(str)  # Convertir todos los datos a cadenas de texto
        personal_df["Estado"] = personal_df["activo"].apply(lambda x: "✅ Activo" if x == "1" else "❌ Inactivo")

        # Configurar AgGrid interactivo
        gb = GridOptionsBuilder.from_dataframe(personal_df)
        gb.configure_pagination(paginationPageSize=10)
        gb.configure_selection('single', use_checkbox=True)
        grid_options = gb.build()

        # Mostrar la tabla con AgGrid
        grid_response = AgGrid(
            personal_df,
            gridOptions=grid_options,
            height=300,
            update_mode=GridUpdateMode.SELECTION_CHANGED
        )
    else:
        st.info("📭 No hay personal registrado. Use el formulario superior para agregar nuevos registros.")
        st.image("https://i.imgur.com/3JGhQnp.png", width=250)

    # --- Edición de Estado ---
    selected_rows = grid_response["selected_rows"]
    if selected_rows:
        with st.expander("✏️ Editar Estado del Personal Seleccionado", expanded=True):
            selected_id = selected_rows[0]["id"]
            nuevo_estado = st.radio(
                "Nuevo Estado:",
                ["✅ Activo", "❌ Inactivo"],
                index=0 if selected_rows[0]["activo"] == "1" else 1
            )
            
            if st.button("Actualizar Estado"):
                try:
                    with engine.connect() as conn:
                        conn.execute(
                            update(personal)
                            .where(personal.c.id == selected_id)
                            .values(activo=1 if nuevo_estado.startswith("✅") else 0)
                        )
                        conn.commit()
                        
                    st.success("Estado actualizado!")
                    st.cache_data.clear()
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Error al actualizar: {str(e)}")
    
# --- Exportación de Datos ---
if not personal_df.empty:
    st.download_button(
        label="📤 Exportar a CSV",
        data=personal_df.to_csv(index=False).encode("utf-8"),
        file_name="personal_autorizado.csv",
        mime="text/csv"
    )
else:
    st.info("📭 No hay personal registrado. Use el formulario superior para agregar nuevos registros.")
    st.image("https://i.imgur.com/3JGhQnp.png", width=250)

# --- Eliminación Segura ---
with st.expander("🗑️ Eliminar Personal", expanded=False):
    if not personal_df.empty:
        personal_a_eliminar = st.selectbox(
            "Seleccionar personal a eliminar:",
            personal_df["nombre_completo"],
            key="delete_personal"
        )
        
        if st.button("Confirmar Eliminación Definitiva", type="primary"):
            try:
                with engine.connect() as conn:
                    # Verificar si el personal está asociado a documentos
                    documentos_asociados = conn.execute(
                        select(documentos)
                        .where(documentos.c.responsable_actualizacion == personal_a_eliminar)
                    ).fetchall()
                    
                    if documentos_asociados:
                        st.error(f"No se puede eliminar: Está asignado en {len(documentos_asociados)} documentos")
                    else:
                        conn.execute(
                            delete(personal)
                            .where(personal.c.nombre_completo == personal_a_eliminar)
                        )
                        conn.commit()
                        st.success(f"{personal_a_eliminar} eliminado")
                        st.cache_data.clear()
            except Exception as e:
                st.error(f"Error crítico: {str(e)}")
    else:
        st.warning("No hay personal para eliminar")
# Tab 6: Ciclo Documental
with tabs[5]:
    st.header("🔄 Ciclo Documental")
    
    # Cargar documentos con verificación de errores
    try:
        documentos_df = cargar_datos()
    except Exception as e:
        st.error(f"Error al cargar documentos: {str(e)}")
        documentos_df = pd.DataFrame()

    if not documentos_df.empty:
        # Selección de documento con verificación de columna
        if "codigo" in documentos_df.columns:
            documento_seleccionado = st.selectbox(
                "Seleccione un documento:",
                documentos_df["codigo"],
                key="ciclo_doc"
            )
            doc_info = documentos_df[documentos_df["codigo"] == documento_seleccionado].iloc[0]
            
            # Estado actual con indicador visual
            col_estado, col_acciones = st.columns([1, 2])
            with col_estado:
                estado_actual = doc_info["estado"]
                color_map = {
                    "Borrador": "gray",
                    "En Revisión": "orange",
                    "Aprobado": "green",
                    "Obsoleto": "red"
                }
                st.markdown(f"""
                *Estado Actual:*  
                <span style='color:{color_map.get(estado_actual, "black")};
                font-weight:bold;font-size:18px'>{estado_actual}</span>
                """, unsafe_allow_html=True)
            
            with col_acciones:
                nuevo_estado = st.selectbox(
                    "Cambiar Estado a:",
                    ["Borrador", "En Revisión", "Aprobado", "Obsoleto"],
                    index=["Borrador", "En Revisión", "Aprobado", "Obsoleto"].index(estado_actual)
                )
                comentarios = st.text_area("Comentarios del Cambio:", height=100)
                
                if st.button("🏷️ Registrar Cambio de Estado", type="primary"):
                    try:
                        with engine.connect() as conn:
                            with conn.begin():
                                # Actualizar estado del documento
                                conn.execute(
                                    documentos.update()
                                    .where(documentos.c.codigo == documento_seleccionado)
                                    .values(estado=nuevo_estado)
                                )
                                
                                # Registrar en histórico de cambios
                                conn.execute(
                                    insert(cambios_estado).values(
                                        documento_codigo=documento_seleccionado,
                                        estado_anterior=estado_actual,
                                        nuevo_estado=nuevo_estado,
                                        comentarios=comentarios,
                                        fecha_cambio=datetime.now()
                                    )
                                )
                                
                        st.success("Estado actualizado e historial registrado!")
                        st.cache_data.clear()
                        st.experimental_rerun()
                        
                    except Exception as e:
                        st.error(f"Error en base de datos: {str(e)}")

            # Histórico de cambios con paginación
            st.subheader("📜 Histórico de Estados")
            try:
                with engine.connect() as conn:
                    historico = pd.read_sql(
                        select(cambios_estado)
                        .where(cambios_estado.c.documento_codigo == documento_seleccionado)
                        .order_by(cambios_estado.c.fecha_cambio.desc()),
                        conn
                    )
                    
                    if not historico.empty:
                        historico["fecha_cambio"] = historico["fecha_cambio"].dt.strftime("%Y-%m-%d %H:%M")
                        gb = GridOptionsBuilder.from_dataframe(historico)
                        gb.configure_pagination(paginationPageSize=5)
                        gb.configure_columns(["id", "documento_codigo"], hide=True)
                        AgGrid(historico, gridOptions=gb.build(), height=200)
                    else:
                        st.info("No hay registro histórico para este documento")
            except Exception as e:
                st.error(f"Error al cargar histórico: {str(e)}")

        else:
            st.error("La columna 'codigo' no existe en los documentos")
    else:
        st.info("📭 No hay documentos registrados. Suba documentos en la pestaña 1 para comenzar")
        st.image("https://i.imgur.com/5m6Ql8f.png", width=300)

    # Sección de próximas revisiones
with st.expander("📅 Próximas Revisiones Programadas", expanded=False):
    if not documentos_df.empty and "fecha_revision" in documentos_df.columns:
        hoy = datetime.now().date()
        
        try:
            # Convertir las fechas con un formato específico
            documentos_df["fecha_revision"] = pd.to_datetime(
                documentos_df["fecha_revision"], format="%d %b %Y", errors="coerce"
            )
            
            # Filtrar las próximas revisiones
            proximas = documentos_df[
                (documentos_df["fecha_revision"].notnull()) &
                (documentos_df["fecha_revision"] > hoy)
            ]
            
            if not proximas.empty:
                st.dataframe(
                    proximas[["codigo", "nombre_documento", "fecha_revision"]],
                    column_config={
                        "fecha_revision": st.column_config.DateColumn(
                            "Próxima Revisión",
                            format="DD/MM/YYYY"
                        )
                    }
                )
            else:
                st.info("No hay revisiones pendientes")
        except Exception as e:
            st.error(f"Error al procesar las fechas de revisión: {str(e)}")
    else:
        st.warning("Datos incompletos para mostrar revisiones")

# Tab 7: Dashboard
with tabs[6]:
    st.header("📊 Dashboard")
    # ... código existente para esta pestaña ...

