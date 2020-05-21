import time
import threading
import shlex
import subprocess
import os
import urllib.request
import zipfile
from helper import (get_pbox_id,									#??
                    send_message_to_popov_service)
													#цикл с выводом

class StatusTask(threading.Thread):
    def is_str_in_cmd_output(cmd, grep_str):
        grep_cmd = '{} | grep -c "{}"'.format(cmd, grep_str)
        try:
            subprocess.check_call(grep_cmd, timeout=30, shell=True)
            return True
        except subprocess.CalledProcessError:
            return False										#проверка службы pbox-devices	

    def is_devices_running(self):
        status_cmd = 'sudo supervisorctl status pbox-devices'
        return self.is_str_in_cmd_output(status_cmd, 'RUNNING')
													#переустановка службы pbox-devices								
    def should_reinstall_devices(self):
        tail_cmd = 'sudo supervisorctl tail pbox-devices'
        status_cmd = 'sudo supervisorctl status pbox-devices'
        tail_result = self.is_str_in_cmd_output(tail_cmd, 'ERROR (no such process name)')
        status_result = self.is_str_in_cmd_output(status_cmd, 'FATAL')
        return tail_result or status_result
													#Запрос логов pbox-devices, вывод ошибки (очистка файлов?)
    def should_clean_pyc(self):
        tail_cmd = 'sudo supervisorctl tail pbox-devices'
        return self.is_str_in_cmd_output(tail_cmd, 'bad marshal data')
													#Запрос логов pbox-devices, вывод ошибки (переустановка зависимостей)
    def should_reinstall_dependencies(self):
        tail_cmd = 'sudo supervisorctl tail pbox-devices'
        return self.is_str_in_cmd_output(tail_cmd, 'ImportError')
													#Запрос логов pbox-devices, вывод ошибки (переустановка пакетов python)

    def should_reinstall_setuptools(self):
        apt_cmd = 'apt list --installed'
        return self.is_str_in_cmd_output(apt_cmd, 'python-setuptools')
													#переустановка зависимостей
    def reinstall_dependencies(self):
        pip_config_file = '/home/pi/.pip/pip.conf'
        local_pip_index = '/home/pi/pip_index'
        pip_index_url = 'https://poster-desktop-update.s3.eu-central-1.amazonaws.com/pip_index.zip'
        rm_venv_cmd = 'sudo rm -rf /opt/pbox-devices/venv'
        venv_cmd = 'sudo virtualenv /opt/pbox-devices/venv'
        reinstall_cmd = ('sudo /opt/pbox-devices/venv/bin/pip install '
                         '-r /opt/pbox-devices/src/requirements.txt '
                         '--find-links {index_dir} --no-index').format(index_dir=local_pip_index)
        send_message_to_popov_service('Reinstalling dependencies')
        if not os.path.isdir(local_pip_index):
            zip_local_pip_index = '/home/pi/pip_index.zip'
            filedata = urllib.request.urlopen(pip_index_url)
            with open(zip_local_pip_index, 'wb') as f:
                f.write(filedata.read())
            with zipfile.ZipFile(zip_local_pip_index, 'r') as zip_ref:
                zip_ref.extractall('/home/pi')
        if not os.path.isfile(pip_config_file):
            if not os.path.exists('/home/pi/.pip'):
                os.mkdir('/home/pi/.pip')
            with open(pip_config_file, 'w') as f:
                f.write(
                    '[global]\nindex-url = file://{index_dir}'.format(index_dir=local_pip_index)
                )
        subprocess.call(shlex.split(rm_venv_cmd), timeout=60)
        subprocess.call(shlex.split(venv_cmd), timeout=60)
        subprocess.call(shlex.split(reinstall_cmd), timeout=60)
													#переустановка пакетов python
    def run(self):
        task_wait_time_minutes = 5
        restart_wait_time_seconds = 45
        while True:
            try:
                if not self.is_devices_running():
                    start_cmd = 'sudo supervisorctl start pbox-devices'
                    subprocess.check_call(shlex.split(start_cmd), timeout=30)
                    time.sleep(restart_wait_time_seconds)
                    if not self.is_devices_running():
                        if self.should_reinstall_setuptools():
                            reinstall_cmd = 'sudo apt-get install python-setuptools'
                            subprocess.call(shlex.split(reinstall_cmd), timeout=60)
                        if self.should_reinstall_devices():
                            reinstall_cmd = 'sudo opkg -f /etc/opkg.conf ' \
                                            'install pbox-devices --force-reinstall'
                            subprocess.call(shlex.split(reinstall_cmd), timeout=60)
                        if self.should_reinstall_dependencies():
                            self.reinstall_dependencies()
                            subprocess.check_call(shlex.split(start_cmd), timeout=30)
                        else:
                            break
            except subprocess.CalledProcessError as e:
                error_msg = 'cmd: {} err: {}'.format(e.cmd, e.returncode)
                send_message_to_popov_service(error_msg)
            finally:
                time.sleep(task_wait_time_minutes * 60)

													#очистка места на пб
class FreeDiskSpaceAmountTask(threading.Thread):
    def run(self):
        space_minimum = 1024
        wait_time_minutes = 5
        while True:
            try:
                data = str(subprocess.check_output(['df', '-m', '/'])).split('\\n')[1]
                data = data.split()
                df_result = {
                    'total': data[1],
                    'user_space': data[2],
                    'available_space': int(data[3]),
                    'percent': data[4],
                }
                available_space = df_result['available_space']
                if available_space < space_minimum:
                    send_message_to_popov_service('Not enough free space')
                    break
            except subprocess.CalledProcessError as e:
                error_msg = 'cmd: {} err: {}'.format(e.cmd, e.returncode)
                send_message_to_popov_service(error_msg)
            finally:
                time.sleep(wait_time_minutes*60)

													#очистка памяти (RAM)
class FreeMemoryAmountTask(threading.Thread):
    def run(self):
        wait_time_minutes = 5
        memory_minimum = 200
        while True:
            try:
                mem_cmd = 'free -m'
                data = str(subprocess.check_output(shlex.split(mem_cmd))).split('\\n')[1]
                data = data.split()
                free_result = {
                    'total': int(data[1]),
                    'used': int(data[2]),
                    'free': data[3],
                    'shared': data[4],
                    'buff/cache': data[5],
                }
                available_memory = free_result['total'] - free_result['used']
                if available_memory < memory_minimum:
                    send_message_to_popov_service('Not enough free memory')
                    break
            except subprocess.CalledProcessError as e:
                error_msg = 'cmd: {} err: {}'.format(e.cmd, e.returncode)
                send_message_to_popov_service(error_msg)
            finally:
                time.sleep(wait_time_minutes*60)
													#логи по вольтажу

class UnderVoltageDetectedTask(threading.Thread):
    def run(self):
        wait_time_minutes = 5
        min_event_occurences = 1
        event_number = 50
        while True:
            try:
                cmd = 'dmesg | tail -n {} | grep -c "Under-voltage detected!"'.format(event_number)
                result = subprocess.check_output(cmd, timeout=30, shell=True).split(b'\n')[0]
                event_occurences = int(result)
                if event_occurences >= min_event_occurences:
                    send_message_to_popov_service('under-voltage', event_occurences)
                    break
            except subprocess.CalledProcessError:
                pass
            finally:
                time.sleep(wait_time_minutes * 60)
													#логи по отпаданию юсб

class USBDisconnectedTask(threading.Thread):
    def run(self):
        wait_time_minutes = 5
        min_event_occurences = 2
        event_number = 50
        while True:
            try:
                cmd = 'dmesg | tail -n {} | grep -c "USB disconnect"'.format(event_number)
                result = subprocess.check_output(cmd, timeout=30, shell=True).split(b'\n')[0]
                event_occurences = int(result)
                if event_occurences >= min_event_occurences:
                    send_message_to_popov_service('USB disconnect', event_occurences)
                    break
            except subprocess.CalledProcessError:
                pass
            finally:
                time.sleep(wait_time_minutes * 60)
													#проблемы с днс, перезапуск pbox-devices

class ResolveDNSTask(threading.Thread):
    def run(self):
        wait_time_minutes = 5
        while True:
            try:
                ping_cmd = 'ping jnpstr.com -c 4'
                try:
                    subprocess.check_call(shlex.split(ping_cmd))
                except subprocess.CalledProcessError as e:
                    send_message_to_popov_service('Can not resolve hostnames')
                    if e.returncode == 1:
                        subprocess.check_call(['sudo', 'resolvconf', '-u', ' '])
                        restart_cmd = 'sudo supervisorctl restart pbox-bot'
                        subprocess.check_call(shlex.split(restart_cmd), timeout=30)
                    continue
            except subprocess.CalledProcessError as e:
                error_msg = 'cmd: {} err: {}'.format(e.cmd, e.returncode)
                send_message_to_popov_service(error_msg)
            finally:
                time.sleep(wait_time_minutes * 60)

													#персонализация
class EmptyConfigTask(threading.Thread):
    def is_config_invalid(self):
        return get_pbox_id() == 'unknown'

    def call_cmd(self, cmd, timeout=30):
        subprocess.check_call(shlex.split(cmd), timeout=timeout)

    def run(self):
        wait_time_minutes = 5
        vpn_data_cmd = 'sudo opkg -f /etc/opkg.conf install pbox-vpn-data --force-reinstall'
        mv_cmd = 'sudo mv /opt/pbox-vpn/config.json-opkg /opt/pbox-vpn/config.json'
        while True:
            try:
                if self.is_config_invalid():
                    send_message_to_popov_service('Invalid bot config')
                    subprocess.call(shlex.split(vpn_data_cmd), timeout=30)
                    self.call_cmd(mv_cmd)
                    self.call_cmd('sudo supervisorctl restart pbox-bot')
                    send_message_to_popov_service('Fix empty config')
            except subprocess.CalledProcessError as e:
                error_msg = 'cmd: {} err: {}'.format(e.cmd, e.returncode)
                send_message_to_popov_service(error_msg)
            finally:
                time.sleep(wait_time_minutes * 60)
