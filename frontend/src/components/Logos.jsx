/**
 * components/Logos.jsx
 * ----------------------
 * Logos de la universidad (UATF) y de la carrera (Ingeniería de Sistemas),
 * reutilizados en portada, login, paneles, documentos y membrete.
 *
 * Son placeholders generados por Stitch (la herramienta de diseño), NO el
 * escudo oficial real de la UATF. Para usar el oficial, colocá los archivos
 * en frontend/public/ y cambiá estas dos constantes por "/logo-uatf.png" y
 * "/logo-sistemas.png".
 */

export const LOGO_UATF =
  "https://lh3.googleusercontent.com/aida-public/AB6AXuDzsVDLZCQh7TFKf0t8nGoTH-FSvYONW5JdFjsj9tiSfLnDnstNat9JoP_0_NIFroNJL_4yz-cq1PuaGSvh7QEnVgyY9FE3agGRlZsYNbRf1_EknklcOLskZeMLLi8zOexZ6KgJvBW6u47LWOIrAiNvAgvSg3_i5-Zkhd26CtFSMI6dC2D3F8wVeWRhOVJGlwDeY1SaGj5hHtUMlGky4hj_yyXeaUk972PkEVW_7nTF3rur7Js8nJAgbdP3uH68s3j7jWE";
export const LOGO_SISTEMAS =
  "https://lh3.googleusercontent.com/aida-public/AB6AXuDjkUYP1K550Pq0w7rEkFWyb0Wu-18YVFIwG6LpK-ZrFWodQS-LeABJ_8vQFSHmcyXKPwncMpKS21HG3Y1LwFuZ3DpkEZeDeuPuDTDExGSzgbr3wmxeEP6eBqoJv65QjKZ2sPxcBXOX-GIwYwQZ7DywD75Ic5L10ymvHQKm8hJ7vw-VssOe0PXMwaSNtSuepQXuna2IjpZmU3cYJ1O-KSQTdN-0HE2JoWUIGJia5U4UE6hc3p59RS9WV1paRcwJtB9uiEw";

// tamano: "sm" (barras y sidebar) | "md" (tarjetas de login) | "lg" (centro de la portada)
export default function Logos({ tamano = "md" }) {
  return (
    <div className={`logos logos--${tamano}`}>
      <img src={LOGO_UATF} alt="Logo UATF" className="logos__img" />
      <img src={LOGO_SISTEMAS} alt="Logo Ingeniería de Sistemas" className="logos__img" />
    </div>
  );
}
