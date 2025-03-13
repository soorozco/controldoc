import re
import io
import streamlit as st
import pandas as pd
import json
from sqlalchemy import create_engine, Table, Column, Integer, String, Text, MetaData, insert, delete, update
import matplotlib.pyplot as plt
from st_aggrid import AgGrid, GridOptionsBuilder
from datetime import datetime

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

# Configuración de la base de datos
def setup_database():
    engine = create_engine('sqlite:///control_documental.db')
    metadata = MetaData()
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
    metadata.create_all(engine)
    return engine, documentos

# Inicialización de la base de datos
engine, documentos = setup_database()

# Configuración de la aplicación Streamlit
st.set_page_config(page_title="Control Documental ISO 9001:2015", layout="wide")
st.title("📋 Sistema de Gestión Documental ISO 9001:2015")

# Pestañas de la aplicación
tabs = st.tabs(["Subir JSON", "Registro y Eliminación", "Detalles y Gestión", "Próximas Revisiones", "Gestión del Ciclo Documental"])

# Función para cargar datos con caché
@st.cache_data
def cargar_datos():
    try:
        with engine.connect() as conn:
            return pd.read_sql("SELECT * FROM documentos", conn)
    except Exception as e:
        st.error(f"Error al cargar los datos: {e}")
        return pd.DataFrame()

# Cargar datos
df = cargar_datos()

# Tab 1: Subir JSON
with tabs[0]:
    st.header("Subir archivo JSON y extraer datos")
    uploaded_json = st.file_uploader("Selecciona un archivo JSON", type=["json"], key="json_upload")
    if uploaded_json is not None:
        json_content = load_json_content(uploaded_json)
        if json_content:
            st.success("Contenido del archivo JSON cargado correctamente.")
            st.json(json_content)
            registro_json = {
                "codigo": json_content.get("Código", ""),
                "nombre_documento": json_content.get("Nombre del Documento", ""),
                "version": json_content.get("Versión vigente", ""),
                "fecha_emision": json_content.get("Fecha de emisión", ""),
                "fecha_revision": json_content.get("Fecha de revisión", ""),
                "objetivo": json_content.get("Objetivo", ""),
                "alcance": json_content.get("Alcance", ""),
                "responsable_actualizacion": json_content.get("Responsabilidades", {}).get("Actualización", ""),
                "responsable_ejecucion": json_content.get("Responsabilidades", {}).get("Ejecución", ""),
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
            with engine.connect() as conn:
                existing = pd.read_sql(f"SELECT * FROM documentos WHERE codigo = '{registro_json['codigo']}'", conn)
                if existing.empty:
                    conn.execute(insert(documentos), registro_json)
                    conn.commit()
                    st.success("Datos extraídos e insertados en la base de datos con estado inicial Borrador.")
                else:
                    st.warning("El documento ya existe en la base de datos.")
            st.cache_data.clear()

# Resto del código...

# Cargar datos
df = cargar_datos()

# Tab 2: Registro y Eliminación
with tabs[1]:
    st.header("Documentos registrados")
    if not df.empty:
        st.dataframe(df[["codigo", "nombre_documento", "version", "fecha_emision", "fecha_revision"]], height=200)
        st.subheader("Eliminar registros")
        codigo_a_eliminar = st.selectbox("Selecciona el documento a eliminar (por código):", df["codigo"])
        if st.button("Eliminar documento", key="delete"):
            if codigo_a_eliminar in df["codigo"].values:
                with engine.connect() as conn:
                    with conn.begin():
                        conn.execute(delete(documentos).where(documentos.c.codigo == codigo_a_eliminar))
                st.success("Documento eliminado.")
                st.cache_data.clear()
            else:
                st.warning("El código seleccionado no existe en la base de datos.")
    else:
        st.info("No hay documentos registrados en la base de datos.")

# Tab 3: Detalles y Gestión
with tabs[2]:
    st.subheader("Detalles del documento seleccionado")
    if not df.empty:
        documento_seleccionado = st.selectbox("Selecciona un documento para ver detalles:", df["codigo"], key="detalle")
        detalles = df[df["codigo"] == documento_seleccionado].iloc[0]

        # Información básica
        st.markdown(f"""
        <div style="background-color:#f0f0f0;padding:10px;border-radius:5px;">
        <strong>Detalles del documento seleccionado</strong><br>
        <strong>Código:</strong> {detalles['codigo']}<br>
        <strong>Nombre del procedimiento:</strong> {detalles['nombre_documento']}<br>
        <strong>Versión:</strong> {detalles['version']}<br>
        <strong>Fecha de Emisión:</strong> {detalles['fecha_emision']}<br>
        <strong>Fecha de Revisión:</strong> {detalles['fecha_revision']}<br>
        </div>
        """, unsafe_allow_html=True)

        # Objetivo y Alcance
        st.markdown(f"""
        <div style="background-color:#e8f4fc;padding:10px;border-radius:5px;margin-top:10px;">
        <strong>Objetivo:</strong> {detalles['objetivo']}<br>
        <strong>Alcance:</strong> {detalles['alcance']}<br>
        </div>
        """, unsafe_allow_html=True)

        # Responsabilidades
        st.markdown(f"""
        <div style="background-color:#fdf6e3;padding:10px;border-radius:5px;margin-top:10px;">
        <strong>Responsable de Actualización:</strong> {detalles['responsable_actualizacion']}<br>
        <strong>Responsable de Ejecución:</strong> {detalles['responsable_ejecucion']}<br>
        <strong>Responsable de Supervisión:</strong> {detalles['responsable_supervision']}<br>
        </div>
        """, unsafe_allow_html=True)

        # Pasos del Procedimiento
        st.subheader("📝 Pasos del procedimiento")
        try:
            pasos_original = json.loads(detalles["pasos"]) if detalles["pasos"] else []
            df_pasos = pd.DataFrame(pasos_original)
            if not df_pasos.empty:
                edited_df = st.data_editor(
                    df_pasos,
                    num_rows="dynamic",
                    use_container_width=True,
                    key=f"editor_{documento_seleccionado}"
                )
                if st.button("Guardar cambios en pasos"):
                    with engine.connect() as conn:
                        with conn.begin():
                            conn.execute(
                                documentos.update()
                                .where(documentos.c.codigo == documento_seleccionado)
                                .values(pasos=json.dumps(edited_df.to_dict(orient="records")))
                            )
            else:
                st.info("No hay pasos registrados.")
        except Exception as e:
            st.error(f"Error al cargar los pasos: {str(e)}")

        # Documentos de Referencia
        st.subheader("📚 Documentos de Referencia")
        try:
            doc_ref = json.loads(detalles["documentos_referencia"]) if detalles["documentos_referencia"] else []
            if isinstance(doc_ref, list) and len(doc_ref) > 0:
                st.table(pd.DataFrame(doc_ref))
            else:
                st.info("No hay documentos de referencia.")
        except Exception as e:
            st.error(f"Error al procesar los documentos de referencia: {str(e)}")

        # Control de Cambios
        st.subheader("🔄 Control de Cambios")
        try:
            cambios = json.loads(detalles["historial_cambios"]) if detalles["historial_cambios"] else []
            if isinstance(cambios, list) and len(cambios) > 0:
                df_cambios = pd.DataFrame(cambios)
                df_cambios = df_cambios.rename(columns={"Número": "No.", "Fecha": "Fecha", "Descripción del Cambio": "Descripción", "Realizado por": "Autor", "Aprobado por": "Aprobador"})
                st.table(df_cambios)
            else:
                st.info("No hay cambios registrados.")
        except Exception as e:
            st.error(f"Error al procesar el control de cambios: {str(e)}")

        # Autorizaciones
        st.subheader("🖋️ Autorizaciones")
        try:
            autorizaciones = json.loads(detalles["autorizaciones"]) if detalles["autorizaciones"] else []
            if isinstance(autorizaciones, list) and len(autorizaciones) > 0:
                st.table(pd.DataFrame(autorizaciones))
            else:
                st.info("No hay autorizaciones registradas.")
        except Exception as e:
            st.error(f"Error al procesar las autorizaciones: {str(e)}")

# Tab 4: Próximas Revisiones
with tabs[3]:
    st.subheader("Próximas revisiones de documentos")
    if not df.empty:
        try:
            df["fecha_revision_dt"] = df["fecha_revision"].apply(
                lambda x: pd.to_datetime(x, format="%d/%m/%Y", errors="coerce")
            )
            proximas_revisiones = df[df["fecha_revision_dt"] > pd.Timestamp.now()].sort_values("fecha_revision_dt")
            if not proximas_revisiones.empty:
                st.table(proximas_revisiones[["codigo", "fecha_revision"]])
            else:
                st.info("No hay próximas revisiones programadas.")
        except Exception as e:
            st.error(f"Error al procesar las fechas de revisión: {e}")
    else:
        st.info("No hay documentos registrados en la base de datos.")

# Tab 5: Gestión del Ciclo Documental
with tabs[4]:
    st.header("📌 Gestión del Ciclo Documental")
    df_gestion = cargar_datos()

    if df_gestion.empty:
        st.info("Actualmente no hay documentos para gestionar.")
    else:
        documento_seleccionado = st.selectbox("Selecciona un documento:", df_gestion["codigo"], key="gestion_doc")
        detalles = df_gestion[df_gestion["codigo"] == documento_seleccionado].iloc[0]

        # Mostrar información básica y estado actual
        st.markdown(f"""
        <div style="background-color:#eaeaea;padding:10px;border-radius:5px;">
            <strong>Documento Seleccionado:</strong> {detalles['nombre_documento']}<br>
            <strong>Estado Actual:</strong> {detalles['estado']}
        </div>
        """, unsafe_allow_html=True)

        # Opciones claras de estado ISO 9001 tradicionales
        nuevo_estado = st.selectbox(
            "Selecciona el nuevo estado del documento:", [
                "Borrador",
                "En Revisión Técnica",
                "Aprobado",
                "Vigente",
                "Obsoleto"
            ],
            index=["Borrador", "En Revisión Técnica", "Aprobado", "Vigente", "Obsoleto"].index(detalles['estado']),
            key="nuevo_estado"
        )

        comentarios_revision = st.text_area("Comentarios sobre el cambio (opcional):", key="comentarios_estado")

        if st.button("Actualizar Estado y Registrar Cambio", key="actualizar_estado"):
            try:
                # Actualizar el historial de cambios
                historial_actualizado = json.loads(detalles["historial_cambios"]) if detalles["historial_cambios"] else []
                historial_actualizado.append({
                    "Número": len(historial_actualizado) + 1,
                    "Fecha": datetime.now().strftime("%d/%m/%Y"),
                    "Descripción del Cambio": f"Cambio de estado de '{detalles['estado']}' a '{nuevo_estado}'",
                    "Realizado por": "Responsable del Sistema",
                    "Aprobado por": "Responsable de Calidad",
                    "Comentarios": comentarios_revision
                })

                # Ejecutar actualización en base de datos
                with engine.connect() as conn:
                    with conn.begin():
                        conn.execute(
                            documentos.update()
                            .where(documentos.c.codigo == documento_seleccionado)
                            .values(
                                estado=nuevo_estado,
                                comentarios_revision=comentarios_revision,
                                historial_cambios=json.dumps(historial_actualizado, ensure_ascii=False)
                            )
                        )

                # Limpiar el caché y recargar datos para reflejar inmediatamente el cambio
                st.cache_data.clear()
                df_gestion = cargar_datos()

                st.success(f"Estado actualizado exitosamente a '{nuevo_estado}'.")
                st.experimental_rerun() # Recarga Streamlit automáticamente

            except Exception as e:
                st.error(f"Ocurrió un error al actualizar el estado: {e}")
