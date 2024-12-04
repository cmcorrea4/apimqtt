import streamlit as st
import paho.mqtt.client as mqtt
import json
from datetime import datetime
import pandas as pd
from collections import deque
import time

# Agregar logs de depuración
def log_debug(message):
    print(f"[DEBUG] {message}")
    if 'debug_messages' not in st.session_state:
        st.session_state.debug_messages = []
    st.session_state.debug_messages.append(f"{datetime.now()}: {message}")

# Configuración MQTT
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "sensor_st"

# Callbacks MQTT
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        log_debug(f"✅ Conectado al broker MQTT. Suscrito a: {MQTT_TOPIC}")
        st.session_state.sensor_data['connected'] = True
        client.subscribe(MQTT_TOPIC)
    else:
        log_debug(f"❌ Error de conexión. Código: {rc}")
        st.session_state.sensor_data['connected'] = False

def on_message(client, userdata, msg):
    try:
        log_debug(f"📨 Mensaje recibido en tópico {msg.topic}")
        payload = json.loads(msg.payload.decode())
        log_debug(f"Datos recibidos: {payload}")
        
        timestamp = datetime.now()
        st.session_state.sensor_data['temp_data'].append(payload.get('Temperatura', 0))
        st.session_state.sensor_data['hum_data'].append(payload.get('Humedad', 0))
        st.session_state.sensor_data['timestamps'].append(timestamp)
        st.session_state.sensor_data['last_temp'] = payload.get('Temperatura', 0)
        st.session_state.sensor_data['last_hum'] = payload.get('Humedad', 0)
    except Exception as e:
        log_debug(f"❌ Error al procesar mensaje: {e}")

def on_disconnect(client, userdata, rc):
    log_debug(f"Desconectado del broker. Código: {rc}")
    st.session_state.sensor_data['connected'] = False

# Inicialización de session state
if 'sensor_data' not in st.session_state:
    st.session_state.sensor_data = {
        'temp_data': deque(maxlen=100),
        'hum_data': deque(maxlen=100),
        'timestamps': deque(maxlen=100),
        'last_temp': 0,
        'last_hum': 0,
        'connected': False,
        'client_id': f'streamlit-client-{int(time.time())}'
    }

# Configuración del cliente MQTT
@st.cache_resource
def get_mqtt_client():
    client = mqtt.Client(client_id=st.session_state.sensor_data['client_id'])
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    try:
        log_debug(f"Intentando conectar a {MQTT_BROKER}:{MQTT_PORT}")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
    except Exception as e:
        log_debug(f"❌ Error al conectar: {e}")
    return client

# UI principal
st.title("📊 Sistema de Monitoreo de Sensores")

# Mostrar estado de depuración
with st.expander("🔍 Debug Info", expanded=True):
    if 'debug_messages' in st.session_state:
        for msg in list(st.session_state.debug_messages)[-5:]:  # Mostrar últimos 5 mensajes
            st.text(msg)
    
    if st.button("Limpiar logs"):
        st.session_state.debug_messages = []

# Cliente MQTT
mqtt_client = get_mqtt_client()

# Interfaz principal
tab1, tab2, tab3 = st.tabs(["Dashboard", "Valores Actuales", "Historial"])

with tab1:
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.session_state.sensor_data['connected']:
            st.success("🟢 Conectado")
        else:
            st.error("🔴 Desconectado")
            
    with col2:
        st.metric("Temperatura", f"{st.session_state.sensor_data['last_temp']}°C")
        
    with col3:
        st.metric("Humedad", f"{st.session_state.sensor_data['last_hum']}%")
    
    if len(st.session_state.sensor_data['temp_data']) > 0:
        df = pd.DataFrame({
            'Timestamp': list(st.session_state.sensor_data['timestamps']),
            'Temperatura': list(st.session_state.sensor_data['temp_data']),
            'Humedad': list(st.session_state.sensor_data['hum_data'])
        })
        
        st.line_chart(df.set_index('Timestamp')['Temperatura'])
        st.line_chart(df.set_index('Timestamp')['Humedad'])
    else:
        st.info("Esperando datos...")

# Script de ejemplo
with st.sidebar.expander("📝 Script de Prueba", expanded=True):
    st.code("""
import paho.mqtt.client as mqtt
import json
import time
import random

# Crear cliente
client = mqtt.Client()

# Conectar al broker
client.connect("broker.hivemq.com", 1883, 60)

# Publicar datos
while True:
    data = {
        "Temperatura": round(random.uniform(20, 30), 1),
        "Humedad": round(random.uniform(40, 80), 1)
    }
    # Publicar en el tópico sensor_st
    client.publish("sensor_st", json.dumps(data))
    print(f"Datos enviados: {data}")
    time.sleep(2)
""", language="python")

# Actualización automática
if st.session_state.sensor_data['connected']:
    time.sleep(2)
    st.rerun()
