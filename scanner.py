import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


def get_service_name(port):
    """Получить имя сервиса для порта."""
    try:
        return socket.getservbyport(port)
    except (OSError, TypeError):
        return "unknown"


def scan_port(host, port, timeout=1):
    """Сканировать один порт."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            return port, (result == 0)
    except (socket.timeout, socket.error) as err:
        return port, False


def validate_input(target, start_port, end_port, timeout):
    """Валидировать входные данные."""
    if not target:
        raise ValueError("Хост не может быть пустым.")

    if start_port < 1 or start_port > 65535:
        raise ValueError("Начальный порт должен быть от 1 до 65535.")

    if end_port < 1 or end_port > 65535:
        raise ValueError("Конечный порт должен быть от 1 до 65535.")

    if start_port > end_port:
        raise ValueError("Начальный порт не может быть больше конечного.")

    if timeout <= 0:
        raise ValueError("Таймаут должен быть положительным числом.")

    return True


def print_progress(current, total):
    """Вывести индикатор прогресса."""
    percent = (current / total) * 100
    print(f"\r[{percent:.1f}%] ({current}/{total})", end="", flush=True)


def resolve_target(target):
    """Преобразовать имя хоста в IP-адрес."""
    try:
        return socket.gethostbyname(target)
    except socket.gaierror as err:
        raise ValueError(f"Не удалось определить хост '{target}': {err}")


def scan_ports(target, start_port, end_port, num_threads=50, timeout=1):
    """Сканирование диапазона портов, возвращает список открытых портов."""
    validate_input(target, start_port, end_port, timeout)
    ip = resolve_target(target)

    num_threads = max(1, min(num_threads, 256))
    total_ports = end_port - start_port + 1

    open_ports = []
    scanned = 0

    print(f"Хост разрешен: {target} -> {ip}")
    print(f"Начинаю сканирование {total_ports} портов c {num_threads} потоками...")

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {
            executor.submit(scan_port, ip, port, timeout): port
            for port in range(start_port, end_port + 1)
        }

        for future in as_completed(futures):
            scanned += 1
            port, is_open = future.result()

            if is_open:
                service = get_service_name(port)
                print(f"[OPEN] Порт {port:5d} | {service:15s}")
                open_ports.append(port)

            print_progress(scanned, total_ports)

    elapsed_time = time.time() - start_time
    print("\n\nСканирование завершено.")
    print(f"Время выполнения: {elapsed_time:.2f} сек")

    return sorted(open_ports)


def print_scan_results(open_ports):
    """Вывести результаты сканирования."""
    if open_ports:
        print(f"\nНайдено открытых портов: {len(open_ports)}")
        print("Открытые порты:")
        for port in open_ports:
            service = get_service_name(port)
            print(f"  {port:5d} - {service}")
    else:
        print("\nОткрытых портов не найдено.")


def main():
    try:
        target = input("Введите IP или хост (по умолчанию localhost): ").strip() or "localhost"
        start_port = int(input("Начальный порт (по умолчанию 1): ") or "1")
        end_port = int(input("Конечный порт (по умолчанию 1000): ") or "1000")
        num_threads = int(input("Количество потоков (по умолчанию 50): ") or "50")
        timeout = float(input("Таймаут (сек, по умолчанию 1.0): ") or "1.0")

        open_ports = scan_ports(target, start_port, end_port, num_threads, timeout)
        print_scan_results(open_ports)
    except KeyboardInterrupt:
        print("\nСканирование прервано пользователем.")
    except (ValueError, socket.error) as err:
        print(f"Ошибка: {err}")
    except Exception as err:
        print(f"Непредвиденная ошибка: {err}")


if __name__ == "__main__":
    main()