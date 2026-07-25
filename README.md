# Contador de Produção com Sensor de Luz (LDR) — ESP32

## Identificação do Candidato

- **Nome completo:** João Emanuel Santos do Nascimento
- **GitHub:** [@joaoeman](https://github.com/joaoeman)
---

## 1. Sobre o projeto

A ideia por trás desse desafio é simples: existem linhas de produção manuais que não têm nenhum tipo de CLP ou sistema automatizado para contar quantas peças passaram durante o turno. Hoje isso é feito no papel, o que é lento e sujeito a erro.

Este projeto simula, dentro do Wokwi, uma solução de baixo custo para esse problema: um sensor de luz (LDR) é posicionado sobre a esteira, e toda vez que uma peça passa por baixo dele, a sombra da peça derruba a leitura de luminosidade por um instante. O firmware do ESP32 interpreta essa queda e a volta da luz como "uma peça passou", soma no contador e informa tudo pela porta serial.

Além de contar peças, o sistema também:

- percebe quando a esteira fica travada (uma peça parada em cima do sensor por tempo demais) e avisa que houve uma **micro-parada**;
- permite reiniciar o turno a qualquer momento apertando um botão físico, zerando os contadores.

Toda a comunicação com quem está operando o sistema acontece via **monitor serial** — não há display nem LEDs, propositalmente, para manter a solução simples e barata.

---

## 2. Como o sistema funciona, passo a passo

O firmware inteiro mora em `src/main.py` e roda em um único laço `while True`, sem nenhuma chamada bloqueante — ou seja, nada de `time.sleep()` longo travando a leitura dos sensores. A cada volta do laço (com uma pequena pausa de 1 ms no final), o código faz o seguinte:

**Passo 1 — Lê o sensor de luz**
O ADC do pino 34 (onde está o LDR) é lido e o valor bruto (0–4095) é convertido para uma porcentagem de "quanto está escuro", através da função `calcular_percentual_luz()`. Quanto maior essa porcentagem, mais luz está sendo bloqueada.

**Passo 2 — Decide se há algo bloqueando o sensor**
Se essa porcentagem passar de 50%, o sistema considera que uma peça está na frente do sensor (`detectado = True`).

**Passo 3 — Trata as três situações possíveis**
1. *Acabou de bloquear* (não estava bloqueado e agora está): o sistema marca `bloqueado = True` e guarda o instante em que isso aconteceu — é o início da contagem de uma possível micro-parada.
2. *Continua bloqueado*: o sistema verifica há quanto tempo isso está acontecendo. Se passar de 5 segundos e ainda não tiver avisado, ele imprime o alerta de micro-parada uma única vez (por isso existe a flag `alerta_emitido`).
3. *Não está mais bloqueado*: se antes estava bloqueado e agora não está mais, significa que a peça passou completamente — é nesse momento, e só nesse momento, que o contador é incrementado. Isso evita contar a mesma peça mais de uma vez enquanto ela ainda está passando na frente do sensor.

**Passo 4 — Lê o botão de reset com debounce**
Em paralelo (dentro do mesmo laço), o botão é lido e comparado com a leitura anterior. Só quando o sinal fica estável por 50 ms ele é aceito como um clique de verdade. Isso evita que um ruído elétrico ou um contato "trepidando" gere múltiplos resets.

**Passo 5 — Reseta o turno**
Quando o clique é confirmado, o contador, o estado de bloqueio e a flag de alerta voltam todos a zero, e o sistema avisa pela serial que o turno foi resetado.

Esse fluxo é o que garante as três mensagens que o CI do Wokwi valida: contagem de peça, alerta de micro-parada e confirmação de reset.

---

## 3. Componentes utilizados na simulação

| Componente | ID no `diagram.json` | Ligação no ESP32 | Papel no projeto |
|---|---|---|---|
| ESP32 DevKit C v4 | `esp` | — | Roda o firmware em MicroPython |
| Fotorresistor (LDR) | `ldr1` | Saída analógica no **GPIO 34** | Detecta a passagem da peça pela variação de luz |
| Botão de pressão | `btn1` | **GPIO 4** (pull-up interno) | Reseta o turno manualmente |
| Monitor Serial | `$serialMonitor` | TX/RX do ESP32 | Mostra inicialização, contagens, alertas e resets |

O botão usa o resistor de pull-up interno do próprio ESP32 — por isso, no código, ele é lido como pressionado quando o valor cai para `0`.

---

## 4. Parâmetros e constantes do firmware

Todos os valores importantes ficam centralizados no topo do arquivo, para facilitar ajustes:

| Parâmetro | Valor | O que controla |
|---|---:|---|
| `porcentagem_ident` | 50% | A partir de quanto bloqueio de luz uma peça é considerada "presente" |
| `DEBOUNCE_MS` | 50 ms | Tempo mínimo de estabilidade para aceitar o clique do botão |
| `LIMITE_MICROPARADA_S` | 5 s | Tempo de bloqueio contínuo para disparar o alerta de micro-parada |
| `ADC_MAX_VALUE` | 4095 | Resolução do ADC (12 bits), usada para normalizar a leitura |

---

## 5. Estrutura do projeto

```text
.
├── binaries/              # Bootloader, tabela de partições e MicroPython (para o build local)
├── scenarios/
│   ├── light/             # Cenários de teste automatizados do Wokwi CI (test_1, test_2, test_3)
│   └── LIGHT.md            # Especificação oficial do desafio escolhido
├── src/
│   └── main.py             # Firmware do contador de produção
├── diagram.json            # Circuito da simulação (ESP32 + LDR + botão)
├── Dockerfile               # Build da imagem usada para gerar o fs.bin
├── flasher_args.json         # Mapeamento dos binários na memória do ESP32
├── requirements.txt          # Dependências Python locais (mpremote)
└── wokwi.toml                # Configuração da simulação Wokwi
```

---

## 6. Como rodar o projeto localmente, passo a passo

### 6.1 Pré-requisitos

- Python 3
- Docker (para gerar o `fs.bin` da mesma forma que o CI faz)
- VS Code com a extensão do Wokwi e uma API Key válida

### 6.2 Instalando as dependências Python

```bash
pip install -r requirements.txt
```

### 6.3 Gerando o arquivo de sistema de arquivos (`fs.bin`)

O ESP32, ao rodar MicroPython, precisa que o código-fonte esteja empacotado num sistema de arquivos LittleFS. Isso é feito em dois passos:

**1) Monta a imagem Docker (só precisa fazer uma vez):**

```bash
docker build -t esp32-builder -f Dockerfile .
```

**2) Gera o `fs.bin` com o conteúdo de `src/` (repita sempre que alterar o `main.py`):**

```bash
docker run --rm -v "$(pwd)/src:/mnt/src" -v "$(pwd):/mnt/out" esp32-builder bash -c "mkdir -p /tmp/fs && cp -r /mnt/src/* /tmp/fs/ && /mklittlefs/mklittlefs -c /tmp/fs -b 4096 -p 256 -s 0x200000 /mnt/out/fs.bin"
```

### 6.4 Rodando a simulação

Com o `fs.bin` gerado na raiz do projeto, basta abrir a pasta no VS Code e iniciar a simulação pela extensão do Wokwi (ela já vai ler `wokwi.toml`, `diagram.json` e `flasher_args.json` automaticamente).

---

## 7. Cenários automatizados (Wokwi CI)

O pipeline de CI roda três cenários, todos dentro de `scenarios/light/`:

| Cenário | O que é simulado | Mensagem esperada na serial |
|---|---|---|
| Contagem normal | Luz cai de 800 lux → 50 lux → volta para 800 lux | `Peca detectada! Total: 1` |
| Micro-parada | Luz permanece em 50 lux por mais de 5 segundos | `Alerta: Micro-parada detectada!` |
| Reset de turno | Botão é pressionado e depois solto | `Turno resetado com sucesso. Contadores zerados.` |

---

## 8. Resultados obtidos

O firmware atende a todos os comportamentos previstos no desafio:

- imprime a mensagem de inicialização assim que o ESP32 liga;
- conta peças apenas quando elas terminam de passar pelo sensor (evitando contagem duplicada);
- detecta obstruções prolongadas sem travar o loop principal;
- dispara apenas um alerta por micro-parada, mesmo que a obstrução continue;
- aplica debounce ao botão e zera corretamente todos os estados do turno.

---

## 9. Comentários adicionais

Os limiares usados (50% de bloqueio, 5 segundos de micro-parada, 50 ms de debounce) foram calibrados para funcionar bem dentro da simulação do Wokwi. Numa esteira real, esses valores provavelmente precisariam de ajuste conforme a iluminação do ambiente e a velocidade da linha.

Como próximos passos, valeria a pena:

- salvar a contagem em memória não volátil, para não perder o turno se o ESP32 reiniciar;
- calcular o tempo médio de ciclo entre peças;
- enviar essas métricas para algum painel de monitoramento externo.

---

> Projeto disponível na **branch `main`** deste repositório.
