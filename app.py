import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client

st.set_page_config(page_title="Actividad Cloud", layout="wide")

# Conexión a Supabase usando secrets de Streamlit
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

if "user_email" not in st.session_state:
    st.session_state.user_email = None

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = None


st.title("Aplicación Cloud - Registro y Análisis de Incidencias")


def login_view():
    st.subheader("Acceso a la aplicación")

    opcion = st.radio("Seleccione una opción", ["Iniciar sesión", "Registrarse"])

    email = st.text_input("Correo")
    password = st.text_input("Contraseña", type="password")

    if opcion == "Registrarse":
        if st.button("Crear cuenta"):
            try:
                supabase.auth.sign_up({
                    "email": email,
                    "password": password
                })
                st.success("Cuenta creada correctamente. Ahora inicia sesión.")
            except Exception as e:
                st.error(f"Error al registrar usuario: {e}")

    if opcion == "Iniciar sesión":
        if st.button("Ingresar"):
            try:
                supabase.auth.sign_in_with_password({
                    "email": email,
                    "password": password
                })
                st.session_state.user_email = email
                st.success("Inicio de sesión correcto.")
                st.rerun()
            except Exception as e:
                st.error(f"Error al iniciar sesión: {e}")


def insertar_registro():
    st.subheader("Registro de datos")

    categoria = st.selectbox(
        "Categoría",
        ["Soporte", "Ventas", "Operaciones", "Calidad", "Tecnología"]
    )

    prioridad = st.slider("Prioridad", 1, 5, 3)
    puntaje = st.slider("Puntaje de satisfacción", 1, 10, 7)

    comentario = st.text_area(
        "Comentario libre",
        placeholder="Escribe una observación o incidencia..."
    )

    canal = st.selectbox("Canal", ["Web", "App móvil", "Correo", "Presencial"])
    sede = st.selectbox("Sede", ["Lima", "Arequipa", "Trujillo", "Cusco"])

    metadata = {
        "canal": canal,
        "sede": sede,
        "registrado_desde": "streamlit"
    }

    if st.button("Guardar registro"):
        nuevo_registro = {
            "source": "app_streamlit",
            "categoria": categoria,
            "prioridad": prioridad,
            "puntaje": puntaje,
            "comentario": comentario,
            "metadata": metadata,
            "user_email": st.session_state.user_email
        }

        try:
            supabase.table("registros_cloud").insert(nuevo_registro).execute()
            st.success("Registro guardado correctamente.")
        except Exception as e:
            st.error(f"Error al guardar registro: {e}")


def cargar_datos():
    try:
        response = (
            supabase
            .table("registros_cloud")
            .select("*")
            .order("created_at", desc=True)
            .limit(1000)
            .execute()
        )

        data = response.data

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
        return df

    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        return pd.DataFrame()


def area_analisis():
    st.subheader("Área de análisis")

    if st.button("Actualizar datos del análisis"):
        st.session_state.df = cargar_datos()
        st.session_state.last_refresh = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if "df" not in st.session_state:
        st.session_state.df = cargar_datos()
        st.session_state.last_refresh = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    df = st.session_state.df

    st.info(f"Última actualización del análisis: {st.session_state.last_refresh}")

    if df.empty:
        st.warning("Todavía no hay datos registrados.")
        return

    ultimo_dato = df["created_at"].max()
    st.caption(f"Último dato insertado en la base de datos: {ultimo_dato}")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total de registros", len(df))

    with col2:
        st.metric("Puntaje promedio", round(df["puntaje"].mean(), 2))

    with col3:
        st.metric("Prioridad promedio", round(df["prioridad"].mean(), 2))

    st.divider()

    st.write("Registros por categoría")
    conteo_categoria = df.groupby("categoria").size().reset_index(name="cantidad")
    st.bar_chart(conteo_categoria, x="categoria", y="cantidad")

    st.write("Promedio de puntaje por categoría")
    promedio_puntaje = df.groupby("categoria")["puntaje"].mean().reset_index()
    st.bar_chart(promedio_puntaje, x="categoria", y="puntaje")

    st.write("Registros por minuto")
    serie_tiempo = (
        df.set_index("created_at")
        .resample("1min")
        .size()
        .reset_index(name="cantidad")
    )
    st.line_chart(serie_tiempo, x="created_at", y="cantidad")

    st.write("Tabla de datos")
    st.dataframe(df, use_container_width=True)


if st.session_state.user_email is None:
    login_view()
else:
    st.sidebar.success(f"Usuario: {st.session_state.user_email}")

    if st.sidebar.button("Cerrar sesión"):
        st.session_state.user_email = None
        st.rerun()

    menu = st.sidebar.radio("Menú", ["Registrar datos", "Análisis"])

    if menu == "Registrar datos":
        insertar_registro()

    if menu == "Análisis":
        area_analisis()
