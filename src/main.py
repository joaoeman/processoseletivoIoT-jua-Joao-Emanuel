from machine import Pin, ADC
import time

# Configuracao de hardware
bottom_pin = Pin(4, Pin.IN, Pin.PULL_UP)
adc_ldr = ADC(Pin(34))
adc_ldr.atten(ADC.ATTN_11DB)

# Parametros definidow
porcentagem_ident = 50
LIMITE_MICROPARADA_S = 5
DEBOUNCE_MS = 50
ADC_MAX_VALUE = 4095

# Estado de contagem
counter = 0
bloqueado = False
alerta_emitido = False
momento = time.ticks_ms()

# Estado do debounce do botao de reset
botao_ultimo_bruto = bottom_pin.value()
botao_estado_estavel = botao_ultimo_bruto
botao_mudou_em = time.ticks_ms()

print("Contador de Producao Inicializado")


def calcular_percentual_luz(valor_bruto):
    return 100 - (valor_bruto / ADC_MAX_VALUE * 100)


while True:
    # Leitura do sensor 
    valor_adc = adc_ldr.read()
    percentual_luz = calcular_percentual_luz(valor_adc)
    detectado = percentual_luz < porcentagem_ident

    if detectado and not bloqueado:
        # Borda de descida: peca acabou de bloquear o sensor.
        # So liga o estado de bloqueio e o cronometro de micro-parada.
        momento = time.ticks_ms()
        bloqueado = True
        alerta_emitido = False

    elif detectado and bloqueado:
        atual = time.ticks_ms()
        if (atual - momento) / 1000 >= LIMITE_MICROPARADA_S and not alerta_emitido:
            print("Alerta: Micro-parada detectada!")
            alerta_emitido = True

    else:
        # Borda de subida: so conta se estava bloqueado antes
        # (peca estava passando e agora saiu de vez).
        if bloqueado:
            counter = counter + 1
            print(f"Peca detectada! Total: {counter}")
        bloqueado = False
        alerta_emitido = False

    # Debounce do botao de reset
    leitura_botao = bottom_pin.value()

    if leitura_botao != botao_ultimo_bruto:
        # O sinal acabou de mudar, ent reinicia a contagem de estabilidade
        botao_ultimo_bruto = leitura_botao
        botao_mudou_em = time.ticks_ms()
    elif time.ticks_diff(time.ticks_ms(), botao_mudou_em) >= DEBOUNCE_MS:
        # O sinal ficou estavel por tempo suficiente, ent aceita como real
        if leitura_botao != botao_estado_estavel:
            botao_estado_estavel = leitura_botao
            if botao_estado_estavel == 1: 
                counter = 0
                bloqueado = False
                alerta_emitido = False
                print("Turno resetado com sucesso. Contadores zerados.")

    time.sleep_ms(1)