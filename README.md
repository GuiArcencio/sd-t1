## Uso

Para utilizar a aplicação, instale as dependências com
```
pip install -r requirements.txt
```
Então, execute o programa com os argumentos:
```
python app.py -r [CÓDIGO DA SALA] -u [NOME DE USUÁRIO] -p [ENDEREÇOS DO PARCEIROS] -b [ENDEREÇO LOCAL]
```
Por exemplo:
```
python app.py --room abcde --username AAA --peer localhost:2002 localhost:2003 --bind 0.0.0.0:2001
```