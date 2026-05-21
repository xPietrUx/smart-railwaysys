FROM node:lts-slim

WORKDIR /app
RUN chown -R node:node /app

COPY --chown=node:node package*.json ./

USER node
RUN npm install

COPY --chown=node:node . .

ENV PORT=5173
EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]