// Prueba de rendimiento con k6 (https://k6.io).
// Uso: k6 run -e BASE_URL=https://IP -e USUARIO=consulta -e CLAVE=xxxx pruebas_carga/k6_busqueda.js
// Nota: el API limita a 1200 peticiones/min por usuario (ver settings.py), por eso 10 usuarios virtuales.
import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  insecureSkipTLSVerify: true, // certificado autofirmado en el laboratorio
  scenarios: {
    busqueda: { executor: "constant-vus", vus: 10, duration: "1m" },
  },
  thresholds: {
    http_req_duration: ["p(95)<1000"], // meta: percentil 95 bajo 1 segundo
    http_req_failed: ["rate<0.01"],
  },
};

export function setup() {
  const r = http.post(
    `${__ENV.BASE_URL}/api/token/`,
    JSON.stringify({ username: __ENV.USUARIO, password: __ENV.CLAVE }),
    { headers: { "Content-Type": "application/json" } }
  );
  return { token: r.json("access") };
}

export default function (datos) {
  const r = http.get(`${__ENV.BASE_URL}/api/calificaciones/?periodo=2024`, {
    headers: { Authorization: `Bearer ${datos.token}` },
  });
  check(r, { "estado 200": (x) => x.status === 200 });
  sleep(1);
}
