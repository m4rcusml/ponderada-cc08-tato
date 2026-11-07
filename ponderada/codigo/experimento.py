"""A4 — buffer circular com duas threads e três políticas de sincronização.

Marcus Felipe dos Santos Valente. Python 3, somente biblioteca padrão.
Os timeouts pertencem ao monitor do experimento; não corrigem os algoritmos.
"""

from collections import Counter
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import platform
import sys
import threading
import time

NOME = "Marcus Felipe dos Santos Valente"
D1 = len(NOME.split()[0]) % 10
D2 = sum(letra.isalpha() for letra in NOME) % 10
N = 3 + D2 % 5
TOTAL = 20_000
LIMITE_SEM_RECEBER = 1.0


def medir(recebidas, produzidas, travou, duracao, estados):
    """Recebe IDs lidos, total produzido, timeout, segundos e estados finais.

    Retorna dicionário de métricas. Perdidas são IDs de 0 a TOTAL-1 ausentes;
    duplicadas são ocorrências válidas além da primeira de cada ID.
    """
    contagem = Counter(x for x in recebidas if isinstance(x, int) and 0 <= x < TOTAL)
    unicas = len(contagem)
    return {
        "produzidas": produzidas,
        "consumidas": len(recebidas),
        "unicas": unicas,
        "perdidas": TOTAL - unicas,
        "nao_produzidas": TOTAL - produzidas,
        "produzidas_nao_recebidas": produzidas - unicas,
        "duplicadas": sum(quantidade - 1 for quantidade in contagem.values()),
        "invalidas": len(recebidas) - sum(contagem.values()),
        "fora_de_ordem": sum(b <= a for a, b in zip(recebidas, recebidas[1:])
                             if isinstance(a, int) and isinstance(b, int)),
        "travou": travou,
        "duracao_s": round(duracao, 6),
        "estados": dict(estados),
    }


def executar(versao):
    """Recebe versão 1, 2 ou 3 e retorna métricas de uma execução de TOTAL IDs.

    Cria buffer e threads novos. O consumidor encerra após TOTAL leituras ou
    um segundo sem receber. Threads bloqueadas da versão 3 são daemon e não
    são desbloqueadas artificialmente pelo monitor.
    """
    if versao not in (1, 2, 3):
        raise ValueError("A versão deve ser 1, 2 ou 3.")
    buffer = [None] * N
    ocupadas = 0
    produzidas = 0
    recebidas = []
    parar = threading.Event()
    vazio = threading.Semaphore(N)
    cheio = threading.Semaphore(0)
    mutex = threading.Semaphore(1)
    estados = {"produtor": "iniciando", "consumidor": "iniciando"}
    travou = False

    def produtor():
        """Sem parâmetros/retorno; publica IDs sequenciais no buffer compartilhado."""
        nonlocal ocupadas, produzidas
        escrita = 0
        for amostra in range(TOTAL):
            if parar.is_set():
                return
            if versao == 1:
                estados["produtor"] = "espera ocupada por espaco"
                while ocupadas >= N:
                    if parar.is_set():
                        return
                buffer[escrita] = amostra
                escrita = (escrita + 1) % N
                anterior = ocupadas
                time.sleep(0)  # Interrupção entre leitura e escrita do contador.
                ocupadas = anterior + 1
            else:
                if versao == 2:
                    estados["produtor"] = "aguardando vazio"
                    vazio.acquire()
                    estados["produtor"] = "aguardando mutex"
                    mutex.acquire()
                else:
                    estados["produtor"] = "aguardando mutex"
                    mutex.acquire()
                    estados["produtor"] = "aguardando vazio (mutex retido)"
                    vazio.acquire()
                buffer[escrita] = amostra
                escrita = (escrita + 1) % N
                mutex.release()
                cheio.release()
            produzidas += 1
        estados["produtor"] = "concluido"

    def consumidor():
        """Sem parâmetros/retorno; lê IDs e sinaliza timeout após 1 s sem progresso."""
        nonlocal ocupadas, travou
        leitura = 0
        ultima = time.monotonic()
        while len(recebidas) < TOTAL:
            if versao == 1:
                estados["consumidor"] = "espera ocupada por amostra"
                while ocupadas <= 0:
                    if time.monotonic() - ultima >= LIMITE_SEM_RECEBER:
                        travou = True
                        parar.set()
                        return
                recebidas.append(buffer[leitura])
                leitura = (leitura + 1) % N
                anterior = ocupadas
                time.sleep(0)
                ocupadas = anterior - 1
            else:
                estados["consumidor"] = "aguardando cheio"
                restante = max(0, LIMITE_SEM_RECEBER - (time.monotonic() - ultima))
                if not cheio.acquire(timeout=restante):
                    travou = True
                    parar.set()
                    return
                estados["consumidor"] = "aguardando mutex (item reservado)"
                restante = max(0, LIMITE_SEM_RECEBER - (time.monotonic() - ultima))
                if not mutex.acquire(timeout=restante):
                    travou = True
                    parar.set()
                    return
                recebidas.append(buffer[leitura])
                leitura = (leitura + 1) % N
                mutex.release()
                vazio.release()
            ultima = time.monotonic()
        estados["consumidor"] = "concluido"
        parar.set()

    inicio = time.monotonic()
    # A mesma ordem de partida é usada nas três versões; o SO decide a intercalação.
    sensor = threading.Thread(target=produtor, name="sensor", daemon=True)
    motor = threading.Thread(target=consumidor, name="motor", daemon=True)
    sensor.start()
    motor.start()
    motor.join()
    sensor.join(timeout=0.05)
    resultado = medir(recebidas, produzidas, travou, time.monotonic() - inicio, estados)
    if versao == 2:
        assert not sensor.is_alive() and not motor.is_alive()
        assert recebidas == list(range(TOTAL)), "FIFO incorreta na versão sincronizada"
        assert not travou
    return resultado


def main(versao):
    """Recebe versão; roda três ensaios, imprime tabela e salva TXT/JSON; retorna None."""
    # A espera ocupada não deve reter o GIL por longas fatias de CPU no ensaio.
    sys.setswitchinterval(0.0001)
    print(f"A4 | {NOME} | D1={D1} D2={D2} N={N}")
    print(f"Python {platform.python_version()} | {platform.system()} {platform.release()}")
    print(f"Versao {versao} | 3 execucoes | {TOTAL} amostras por execucao | timeout=1 s", flush=True)
    linhas = ["exec produzidas consumidas perdidas duplicadas travou duracao_s"]
    resultados = []
    for numero in range(1, 4):
        r = executar(versao)
        r["execucao"] = numero
        resultados.append(r)
        linha = (f"{numero:4d} {r['produzidas']:10d} {r['consumidas']:10d} "
                 f"{r['perdidas']:8d} {r['duplicadas']:10d} "
                 f"{'sim' if r['travou'] else 'nao':>6s} {r['duracao_s']:.6f}")
        linhas.append(linha)
        print(linhas[0] if numero == 1 else "", end="\n" if numero == 1 else "")
        print(linha, flush=True)
        print(f"     produtor: {r['estados']['produtor']}; consumidor: {r['estados']['consumidor']}")
    dados = {
        "nome": NOME, "D1": D1, "D2": D2, "N": N, "total": TOTAL,
        "versao": versao, "python": sys.version, "sistema": platform.platform(),
        "intervalo_troca_python_s": sys.getswitchinterval(),
        "data": datetime.now(timezone(timedelta(hours=-3))).isoformat(),
        "resultados": resultados,
    }
    pasta = Path(__file__).resolve().parent
    (pasta / f"resultados_v{versao}.json").write_text(
        json.dumps(dados, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (pasta / f"resultados_v{versao}.txt").write_text(
        f"A4 — {NOME} — D1={D1} D2={D2} N={N}\nVersão {versao}\n"
        + "\n".join(linhas) + "\n", encoding="utf-8")
