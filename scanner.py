import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse


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


def parse_ports(ports_str):
    """Парсинг аргумента --ports."""
    if ports_str == "all":
        return list(range(1, 65536))
    elif '-' in ports_str:
        try:
            start, end = map(int, ports_str.split('-'))
            if start < 1 or end > 65535 or start > end:
                raise ValueError
            return list(range(start, end + 1))
        except ValueError:
            raise ValueError(f"Неверный диапазон портов: {ports_str}. Используйте формат start-end, например 1-1000")
    else:
        try:
            ports = [int(p.strip()) for p in ports_str.split(',')]
            if any(p < 1 or p > 65535 for p in ports):
                raise ValueError
            return ports
        except ValueError:
            raise ValueError(f"Неверный список портов: {ports_str}. Используйте формат port1,port2,port3, например 80,443,22")


def resolve_target(target):
    """Преобразовать имя хоста в IP-адрес."""
    try:
        return socket.gethostbyname(target)
    except socket.gaierror as err:
        raise ValueError(f"Не удалось определить хост '{target}': {err}")


def print_progress(current, total, start_time):
    """Вывести улучшенный индикатор прогресса."""
    percent = (current / total) * 100
    elapsed = time.time() - start_time
    eta = (elapsed / current) * (total - current) if current > 0 else 0
    
    # Визуальный бар
    bar_length = 30
    filled = int(bar_length * percent / 100)
    bar = '█' * filled + '░' * (bar_length - filled)
    
    print(f"\r[{bar}] {percent:.1f}% ({current}/{total}) | Время: {elapsed:.1f}с | ETA: {eta:.1f}с", end="", flush=True)


def scan_ports(target, ports_list, num_threads=50, timeout=1):
    """Сканирование списка портов, возвращает список открытых портов."""
    ip = resolve_target(target)

    num_threads = max(1, min(num_threads, 256))
    total_ports = len(ports_list)

    open_ports = []
    scanned = 0

    print(f"Хост разрешен: {target} -> {ip}")
    print(f"Начинаю сканирование {total_ports} портов c {num_threads} потоками...")

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {
            executor.submit(scan_port, ip, port, timeout): port
            for port in ports_list
        }

        for future in as_completed(futures):
            scanned += 1
            port, is_open = future.result()

            if is_open:
                open_ports.append(port)

            print_progress(scanned, total_ports, start_time)

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
    parser = argparse.ArgumentParser(description="Многопоточный TCP-сканер портов")
    parser.add_argument("--host", default="localhost", help="IP или хост для сканирования (по умолчанию: localhost)")
    parser.add_argument("--ports", default="1-1000", help="Диапазон или список портов: диапазон (1-1000), список (80,443,22) или all (по умолчанию: 1-1000)")
    parser.add_argument("--threads", type=int, default=50, help="Количество потоков (по умолчанию: 50)")
    parser.add_argument("--timeout", type=float, default=1.0, help="Таймаут в секундах (по умолчанию: 1.0)")

    args = parser.parse_args()

    # Парсинг портов
    try:
        ports_list = parse_ports(args.ports)
    except ValueError as err:
        parser.error(str(err))

    # Валидация других аргументов
    if args.threads < 1:
        parser.error("Количество потоков должно быть положительным")
    if args.timeout <= 0:
        parser.error("Таймаут должен быть положительным")

    try:
        open_ports = scan_ports(args.host, ports_list, args.threads, args.timeout)
        print_scan_results(open_ports)
    except KeyboardInterrupt:
        print("\nСканирование прервано пользователем.")
    except (ValueError, socket.error) as err:
        print(f"Ошибка: {err}")
    except Exception as err:
        print(f"Непредвиденная ошибка: {err}")


if __name__ == "__main__":
    main()