Esse arquivo é para documentar a linha de pensamento do Matheus ao ir avançando com o desenvolvimento do desafio. Acrido que o que será avaliado é a forma de pensar, então quero ir compartilhando tudo que estou pensando durante a construção, pois acredito que isso pode ajudar na avaliação.

Quando eu recebi o teste, na sexta-feira, dia 14/08, eu li com atenção a descrição do desafio, como já tinha trabalhado o dia todo, deixei para começar a estudar o desafio depois de descansar a mente por algumas horas. Por sorte, não tive aula na faculdade

A primeira coisa que veio na cabeça é como fazer o teste, uma vez que boa parte da minha experiência em modelagem veio da área de Fraude e agora eu teria que prever dados de atleta para o cartola, que é um assunto que eu nunca tinha tido contato. 

A primeira coisa que fiz foi uma busca para entender como nasceu a ideia de prever performance de jogadores, quem já tinha feito isso, quais teses e dissertaçòes existiam sobre o assunto, até que cheguei em alguns nomes que me ajudaram a entender o cenário de forma macro. Foi essas referencias que eu utilizei no Gemini LM para me apoiar e entender com as mentes que já fizeram isso antes.

### Tabela de Referências

| Nome do Autor | Nome do Artigo / Repositório | Orientador(es) / Supervisor(es) | Descrição |
| :--- | :--- | :--- | :--- |
| **VISCONDI**, Gabriel F.; **JUSTO**, Diógenes; **GARCÍA**, Nelson M. | Aplicação de aprendizado de máquina para otimização da escalação de time no jogo Cartola FC | Não aplicável *(Trabalho desenvolvido no âmbito da disciplina de pós-graduação PCS5031 da USP)* | **Autores**: VISCONDI, Gabriel F.; JUSTO, Diógenes; GARCÍA, Nelson M.<br>**Título**: Aplicação de aprendizado de máquina para otimização da escalação de time no jogo Cartola FC.<br>**Evento**: **PCS5031 - Introdução à Ciência dos Dados (Escola Politécnica da USP)**<br>**Ano**: 2017.<br>**Link**: <https://github.com/diogenesjusto/PCS5031>. |
| **COSTA**, Ígor Barbosa da | Modelagem e predição de resultados de futebol antes e durante as partidas usando aprendizagem de máquina | Prof. Dr. **Carlos Eduardo Santos Pires** *(Orientador - UFCG)*<br>Prof. Dr. **Leandro Balby Marinho** *(Coorientador - UFCG)* | **Autores**: COSTA, Ígor Barbosa da.<br>**Título**: Modelagem e predição de resultados de futebol antes e durante as partidas usando aprendizagem de máquina.<br>**Revista/Evento**: **Tese (Doutorado em Ciência da Computação) – UFCG**<br>**Ano**: 2021.<br>**Link**: <https://github.com/igormago/doutorado>. |
| **HEDAR**, Sara | Applying Machine Learning Methods to Predict the Outcome of Shots in Football | **Ather Gattami** *(Supervisor/Handledare)*<br>**David Sumpter** *(Subject Reader/Ämnesgranskare)* | **Autores**: HEDAR, Sara.<br>**Título**: Applying Machine Learning Methods to Predict the Outcome of Shots in Football.<br>**Revista/Evento**: **Examensarbete (Uppsala Universitet - Teknisk-naturvetenskaplig fakultet)**<br>**Ano**: 2020.<br>**Link**: <https://www.diva-portal.org/smash/get/diva2:1448482/FULLTEXT01.pdf>. |
| **NORGREN**, Ofelia | Determining the Quality of Possessions in Football | **Mirjam Bruinsma** *(Supervisor - AFC Ajax / Uppsala University)*<br>**David J.T. Sumpter** *(Subject Reader)* | **Autores**: NORGREN, Ofelia.<br>**Título**: Determining the Quality of Possessions in Football.<br>**Revista/Evento**: **Degree Project (Uppsala Universitet em colaboração com o AFC Ajax)**<br>**Ano**: 2024.<br>**Link**: <https://www.diva-portal.org/smash/get/diva2:1914675/FULLTEXT01.pdf>. |
| **GOMIDE**, Henrique; **GUALBERTO**, Arnaldo | caRtola | Não aplicável *(Repositório Open Source no GitHub)* | **Autor ou Organização**: GOMIDE, Henrique; GUALBERTO, Arnaldo.<br>**Título do repositório**: **caRtola**<br>**Ano**: 2022.<br>**Link**: <https://github.com/henriquepgomide/caRtola>. |


Principais Destaques dos Orientadores Identificados:
David Sumpter (Uppsala University): Atuou ativamente na validação científica dos modelos de predição de chutes a gol da Sara Hedar e nas métricas de qualidade de posse de bola (em parceria com o departamento de análise do **AFC Ajax**) da Ofelia Norgren.

após fazer esse levantamento, comecei a ir para o código. Como de costume, eu utilizo o Antigravity 2.0 como IDE de desenvolvimento, mas dessa vez foi uma surpresa, pois quando eu clonei o repositório, trouxe o contexto e dei o primeiro comando no chat ele já construiu a solução ponta a ponta, que está documentado no repositório: https://github.com/mromaoro/desafio-tecnico-gato-mestre

(reescreva o texto acima com esse direcional:

Apresentar isso como uma metodologia deliberada de aceleração e engenharia reversa demonstra maturidade técnica de ponta:

Exploração e Prototipação Acelerada: Você usou um ecossistema multiagente (Antigravity) para gerar um baseline estrutural e estressar o fluxo de ponta a ponta (verificação de endpoints, schemas de saída, contratos de API).

Auditoria Crítica e Rigor Científico: Ao analisar o código gerado, você identificou onde os agentes tomam "atalhos" ingênuos típicos (como simplificações em data leakage temporal, tratamento superficial de scouts ou falta de robustez nas políticas de retry da API).

Construção Manual com Domínio e Decisão Técnica: A entrega principal reflete o seu domínio analítico, onde cada decisão de modelagem, separação de janelas temporais e métrica de negócio foi deliberadamente escolhida e validada por você.)

Geralmente eu utilizo a metodologia de criar o baseline e ir melhorando, mas nesse caso optei por fazer diferente, utilizei a IA para construir a solução do começo ao fim, auditei o código dela e construi o meu sobre essa base.

A principal vantagem desse approach é que ele me permitiu ter uma visão de ponta a ponta do problema, desde a ingestão dos dados até a entrega do modelo, além de me permitir validar minhas hipóteses com rapidez e aprimorar minha estratégia inicial.

Quando eu criava modelos em prevenção a fraude, era 3 meses de tabalho. Agora, em 30 minutos já conseguimos ter a solução de ponta a ponta e melhorar.

No sábado, reservei o começo do dia para traçar a estratégia de modelagem, revisatar os conceitos principais e o período da tarde iniciar a modelagem, mas com a seguinte rule no agente do antigravity:

(Atue como Ferramenta Restrita: A partir de agora, você é um assistente de desenvolvimento sob demanda. O raciocínio arquitetural, as decisões de modelagem de machine learning e a estratégia são de minha total responsabilidade.

Proibição de Código Autônomo: Você está expressamente proibido de gerar a solução completa do projeto, criar múltiplos arquivos de uma vez ou avançar para etapas futuras por conta própria.

Execução Cirúrgica: Execute estritamente a micro-tarefa que eu solicitar. Ao terminar, pare a geração e aguarde meu próximo comando.

Aprovação Prévia: Se eu pedir para você estruturar uma função complexa, primeiro escreva o plano lógico em tópicos. Só gere o código final após a minha aprovação explícita.

Foco em Trade-offs: Quando eu fizer uma pergunta técnica, não me dê a resposta final. Forneça opções e trade-offs matemáticos ou de engenharia para que eu tome a decisão.)

Inicie o desenvolvimento do desafio. A partir de agora, vou documentando aqui as grandes questões que fui tendo e como foi o avanço.

