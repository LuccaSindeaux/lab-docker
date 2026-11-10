# Requisitos importantes

- Arquivo Dockerfile deve ser com D maiúsculo. 

- No terminal:

Criar rede isolada
```docker network create rede-app```

Subir container no Redis
```docker run -d --name banco-redis --network rede-app redis:alpine```

Construir a imagem da aplicação
```docker build -t minha-app-python .```

Criar a pasta logs localmente no projeto
```mkdir logs```

Subir a aplicação conectando rede, porta e volume
```docker run -d --name web-app --network rede-app -p 5000:5000 -v ${PWD}/logs:/var/log/app minha-app-python```