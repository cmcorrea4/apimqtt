import streamlit as st
import paho.mqtt.client as mqtt
import json
from datetime import datetime
import pandas as pd
from collections import deque
import time
import os

# Configuración de la página
st.set_page_config(
    page_title="Sistema de Monitoreo de Sensores",
    page_icon="🌡️",
    layout="wide"
)

# Configuración MQTT - Usando HiveMQ público
MQTT_BROKER = "broker.hivemq.com"  # Broker público
MQTT_PORT = 1883
MQTT_TOPIC = "sensores/temperatura-humedad"  # Tópico único para evitar conflictos

# Inicialización de variables en session state
if 'sensor_data' not in st.session_state:
    st.session_state.sensor_data = {
        'temp_data': deque(maxlen=100),
        'hum_data': deque(maxlen=100),
        'timestamps': deque(maxlen=100),
        'last_temp': 0,
        'last_hum': 0,
        'connected': False,
        'client_id': f'streamlit-client-{int(time.time())}'  # ID único para cada instancia
    }

# Callbacks MQTT
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        st.session_state.sensor_data['connected'] = True
        client.subscribe(MQTT_TOPIC)
    else:
        st.session_state.sensor_data['connected'] = False

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        timestamp = datetime.now()
        
        # Actualizar datos
        st.session_state.sensor_data['temp_data'].append(payload.get('Temperatura', 0))
        st.session_state.sensor_data['hum_data'].append(payload.get('Humedad', 0))
        st.session_state.sensor_data['timestamps'].append(timestamp)
        st.session_state.sensor_data['last_temp'] = payload.get('Temperatura', 0)
        st.session_state.sensor_data['last_hum'] = payload.get('Humedad', 0)
    except Exception as e:
        st.error(f"Error al procesar mensaje: {e}")

# Configuración del cliente MQTT
@st.cache_resource
def get_mqtt_client():
    client = mqtt.Client(client_id=st.session_state.sensor_data['client_id'])
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
    except Exception as e:
        st.error(f"Error al conectar al broker MQTT: {e}")
    return client

# Iniciar cliente MQTT
mqtt_client = get_mqtt_client()

# Sidebar para API y configuración
st.sidebar.title("API Endpoints")
endpoint = st.sidebar.radio(
    "Seleccionar Endpoint",
    ["Dashboard", "Current Values", "History"]
)

# Información de conexión en el sidebar
st.sidebar.divider()
st.sidebar.subheader("Información de Conexión")
st.sidebar.code(f"""
Broker: {MQTT_BROKER}
Puerto: {MQTT_PORT}
Tópico: {MQTT_TOPIC}
""")

# Script de ejemplo en el sidebar
with st.sidebar.expander("Script de Prueba"):
    st.code("""
import paho.mqtt.client as mqtt
import json
import time
import random

client = mqtt.Client()
client.connect("broker.hivemq.com", 1883, 60)

while True:
    data = {
        "Temperatura": round(random.uniform(20, 30), 1),
        "Humedad": round(random.uniform(40, 80), 1)
    }
    client.publish("sensores/temperatura-humedad", 
                  json.dumps(data))
    time.sleep(2)
    """, language="python")

# Contenido principal
if endpoint == "Dashboard":
    st.title("📊 Dashboard de Sensores en Tiempo Real")
    
    # Estado de conexión y métricas
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.session_state.sensor_data['connected']:
            st.success("🟢 Conectado al broker MQTT")
        else:
            st.error("🔴 Desconectado del broker MQTT")
            
    with col2:
        st.metric(
            "Temperatura",
            f"{st.session_state.sensor_data['last_temp']}°C"
        )
        
    with col3:
        st.metric(
            "Humedad",
            f"{st.session_state.sensor_data['last_hum']}%"
        )
    
    # Gráficos y datos
    if len(st.session_state.sensor_data['temp_data']) > 0:
        df = pd.DataFrame({
            'Timestamp': list(st.session_state.sensor_data['timestamps']),
            'Temperatura': list(st.session_state.sensor_data['temp_data']),
            'Humedad': list(st.session_state.sensor_data['hum_data'])
        })
        
        # Gráfico de temperatura
        st.subheader("Histórico de Temperatura")
        st.line_chart(df.set_index('Timestamp')['Temperatura'])
        
        # Gráfico de humedad
        st.subheader("Histórico de Humedad")
        st.line_chart(df.set_index('Timestamp')['Humedad'])
        
        # Tabla de datos recientes
        st.subheader("Últimas Mediciones")
        st.dataframe(df.tail(10).sort_index(ascending=False))
    else:
        st.info("Esperando datos de los sensores...")

elif endpoint == "Current Values":
    st.title("🔍 Valores Actuales")
    
    current_data = {
        "timestamp": datetime.now().isoformat(),
        "temperatura": st.session_state.sensor_data['last_temp'],
        "humedad": st.session_state.sensor_data['last_hum']
    }
    
    st.json(current_data)
    
    if st.button("Actualizar valores"):
        st.experimental_rerun()

elif endpoint == "History":
    st.title("📜 Historial de Mediciones")
    
    if len(st.session_state.sensor_data['timestamps']) > 0:
        history_df = pd.DataFrame({
            'timestamp': list(st.session_state.sensor_data['timestamps']),
            'temperatura': list(st.session_state.sensor_data['temp_data']),
            'humedad': list(st.session_state.sensor_data['hum_data'])
        })
        
        format_option = st.selectbox(
            "Formato de salida",
            ["Tabla", "JSON"]
        )
        
        if format_option == "Tabla":
            st.dataframe(history_df)
        else:
            st.json(history_df.to_dict('records'))
    else:
        st.info("No hay datos históricos disponibles")

# Actualización automática
time.sleep(0.1)
st.experimental_rerun()
