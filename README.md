# Marcus Felipe dos Santos Valente

Análise técnica e decisão de produção da pulseira sensorial Tato — ponderada de Computação CC08.

O trabalho está em [ponderada/ponderada-tato.md](ponderada/ponderada-tato.md).
Parâmetros: **D1 = 6, D2 = 8, N = 6**.

## Executar a questão A4

Requisito: Python 3 com `threading`, sem dependências externas. Execute os comandos na raiz deste repositório. No Linux/macOS, use `python3` no lugar de `python`.

```sh
python ponderada/codigo/versao1.py
```

```sh
python ponderada/codigo/versao2.py
```

```sh
python ponderada/codigo/versao3.py
```

Cada comando roda **três execuções com meta de 20.000 amostras**, imprime os resultados e grava `resultados_vN.json` e `resultados_vN.txt` em `ponderada/codigo`. Rodar novamente substitui esses dois registros da versão; os prints da entrega permanecem em `ponderada/img`.

- **Versão 1:** buffer circular com contador sem proteção, espera ocupada e `time.sleep(0)` entre ler e escrever o contador.
- **Versão 2:** semáforos `vazio = N`, `cheio = 0` e `mutex = 1`, com aquisição correta.
- **Versão 3:** o produtor adquire `mutex` antes de `vazio`, permitindo deadlock.

`experimento.py` contém a implementação compartilhada e a apuração das métricas. As versões 2 e 3 diferem somente na ordem de aquisição dos semáforos pelo produtor. O consumidor registra travamento se passar um segundo sem receber uma amostra; as esperas com timeout servem ao monitor, sem corrigir o algoritmo defeituoso. Threads bloqueadas são daemon e terminam com o processo Python.

O consumidor encerra ao completar 20.000 leituras ou pelo timeout. Leituras duplicadas podem fazê-lo atingir essa quantidade antes de receber todos os IDs distintos. Por isso os registros incluem amostras produzidas, distintas, não produzidas e produzidas não recebidas. Perdas consideram os 20.000 IDs esperados; não significam necessariamente descarte de 20.000 itens já produzidos.

O ensaio usa intervalo de troca do interpretador de 0,1 ms, igual nas três versões, para ampliar as intercalações sem longas retenções do GIL na espera ocupada. A geração ocorre tão rápido quanto possível, sem simular o período de 10 ms da pulseira. Os resultados das versões defeituosas variam conforme o escalonamento. A versão 2 verifica também a sequência FIFO completa com `assert`.

## Estrutura

```text
README.md
.gitignore
ponderada/
  ponderada-tato.md
  codigo/
    experimento.py
    versao1.py
    versao2.py
    versao3.py
    resultados_v1.json / .txt
    resultados_v2.json / .txt
    resultados_v3.json / .txt
  img/
    caches-cpuz.png
    a4-versao1.png
    a4-versao2.png
    a4-versao3.png
```

Tag de entrega: `PONDERADA-CC08`.
