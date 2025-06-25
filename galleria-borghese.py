import asyncio
from playwright.async_api import async_playwright, TimeoutError

URL = "https://www.tosc.it/artist/galleria-borghese/galleria-borghese-2253937/"


async def revisar_disponibilidad():
    async with async_playwright() as p:
        # Usar contexto persistente para mantener cookies
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./browser_data",
            headless=False,  # Cambia a True para modo sin interfaz
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        page = await context.new_page()

        print(f"🔍 Abriendo la página: {URL}")
        try:
            await page.goto(URL, timeout=30000)
        except Exception as e:
            print(f"⚠️ Error al cargar la página: {e}")
            await context.close()
            return

        # Aceptar cookies
        try:
            await page.wait_for_selector("a.cmpboxbtnyes", timeout=10000)
            await page.click("a.cmpboxbtnyes")
            print("🍪 Cookies aceptadas.")
        except TimeoutError:
            print("⚠️ No apareció el botón de cookies.")

        # Esperar que cargue el calendario
        try:
            await page.wait_for_selector("div.event-information", state="attached", timeout=20000)
            print("✅ Calendario cargado")
        except TimeoutError:
            print("⚠️ No se cargó el calendario.")
            await context.close()
            return

        meses_a_revisar = 4  # Cantidad de meses para revisar

        for ciclo in range(meses_a_revisar):
            print(f"\n🔎 Mes {ciclo + 1}")

            # Obtener días y eventos
            try:
                dias_fecha = await page.query_selector_all("div.cal-cell1.cal-cell")
                print("dia_fecha")
                print(f"  - Encontrados {len(dias_fecha)} días")
                dias_evento = await page.query_selector_all("div.event-information")
                print("dias_evento")
                print(f"  - Encontrados {len(dias_evento)} eventos")
            except Exception as e:
                print(f"⚠️ Error al obtener días/eventos: {e}")
                break

            if not dias_fecha or not dias_evento:
                print("⚠️ No se encontraron días o eventos en el calendario.")
                break

            min_len = min(len(dias_fecha), len(dias_evento))
            print("min_len")
            print(min_len)

            for i in range(min_len):
                print(f"i in range min_len: {i}")
                # Refrescar elementos para evitar DOM inválido
                dias_fecha = await page.query_selector_all("div.cal-cell1.cal-cell")
                dias_evento = await page.query_selector_all("div.event-information")

                # Verificar que el índice sea válido
                if i >= len(dias_fecha) or i >= len(dias_evento):
                    print(f"⚠️ Índice {i} fuera de rango para dias_fecha o dias_evento")
                    continue

                dia = dias_fecha[i]
                evento = dias_evento[i]
                print("dentro del bucle")
                print("dia")
                print(dia)
                print("evento")
                print(evento)

                # Obtener la fecha
                try:
                    day_span = await dia.query_selector("span.day-number")
                    print("day_span")
                    print(day_span)
                    fecha = await day_span.get_attribute("data-cal-date") if day_span else "Fecha desconocida"
                    print("fecha")
                    print(fecha)
                    clase = await day_span.get_attribute("class") if day_span else ""
                    print("clase")
                    print(clase)
                    clase_str = str(clase)
                    if "cal-event-status-available" in clase_str:
                        print("available")
                        print(fecha)
                        # Hacer clic en el día
                        await dia.click()
                        await page.wait_for_timeout(3000)  # Esperar a que la UI se estabilice

                        # Buscar el botón biglietti
                        boton_biglieti = await page.query_selector('button[data-qa="calendar-event-next-button"]')
                        if boton_biglieti:
                            print("✅ Botón 'biglietti' encontrado")
                            await boton_biglieti.click()
                            try:
                                await page.wait_for_selector("div.ticket-type-list", state="visible", timeout=15000)
                                print("✅ Botón 'biglietti' clickeado")
                            except TimeoutError:
                                print(f"⚠️ No se cargó el panel de tickets para {fecha}")
                                continue

                            # Verificar si hay iframe
                            iframe = await page.query_selector("iframe")
                            if iframe:
                                print("🔍 Detectado iframe, cambiando contexto")
                                frame = await iframe.content_frame()
                                if frame:
                                    page = frame

                            # Buscar el contenedor ticket-type-list
                            ticket_list = await page.query_selector("div.ticket-type-list")
                            if ticket_list:
                                print("✅ Contenedor ticket-type-list encontrado")

                                # Buscar divs disponibles
                                divs_disponibles = await ticket_list.query_selector_all(
                                    "div.ticket-type-wrapper:not(:has(.ticket-type-unavailable-sec))"
                                )

                                if divs_disponibles:
                                    print(f"✅ Encontrados {len(divs_disponibles)} horarios disponibles:")
                                    for div in divs_disponibles:
                                        # Buscar el horario en el ancestro event-list-item-wrapper
                                        parent = await div.query_selector(
                                            "xpath=ancestor::div[contains(@class, 'event-list-item-wrapper')]"
                                        )
                                        if parent:
                                            horario_elem = await parent.query_selector("div.pc-list-category span")
                                            if horario_elem:
                                                horario = await horario_elem.inner_text()
                                                print(f"  - {fecha}: {horario.strip()}")
                                            else:
                                                print(f"  - Horario no encontrado para {fecha}")
                                else:
                                    print("⚠️ No se encontraron horarios disponibles.")
                                    # Depuración: Imprimir HTML del contenedor
                                    html = await ticket_list.inner_html()
                                    print(f"🔍 HTML del contenedor ticket-type-list: {html[:1000]}...")
                            else:
                                print(f"⚠️ No se encontró el contenedor 'ticket-type-list' para {fecha}")
                        else:
                            print(f"⚠️ No se encontró el botón 'biglietti' para {fecha}")
                except Exception as e:
                    print(f"⚠️ Error al procesar día {fecha}: {e}")
                    continue

            # Avanzar al siguiente mes
            try:
                boton_siguiente = await page.query_selector('button[data-calendar-nav="next"]')
                if boton_siguiente:
                    await boton_siguiente.click()
                    await page.wait_for_timeout(6000)  # Esperar carga del mes siguiente
                    print("✅ Avanzado al siguiente mes")
                else:
                    print("⚠️ No se encontró el botón para avanzar el calendario")
                    break
            except Exception as e:
                print(f"⚠️ Error al avanzar al siguiente mes: {e}")
                break

        # Cerrar el contexto fuera del bucle
        await context.close()


if __name__ == "__main__":
    asyncio.run(revisar_disponibilidad())
