import os
import sys
import urllib
import urllib2
import zipfile
import gevent
import random
import string

from subprocess import call
from datetime import datetime
from socketio.namespace import BaseNamespace


class SetwpNamespace(BaseNamespace):
    """
    Class to setup a WordPress Installation
    This class is served using zerorpc
    """

    def initialize(self):
        """
        Initialization function for SetupWP
        This function saves the
        """

        self.regions = [
            {
                "id": "local",
                "name": "Localhost",
                "domain": "localhost",
                "folder": "/Applications/XAMPP/htdocs",
                "mysqlUsername": "root",
                "mysqlPassword": ""
            },
            {
                "id": "hangzhou",
                "name": "Hangzhou",
                "domain": "114.215.179.27",
                "folder": "/home/sparkplug/public_html/boxes",
                "mysqlUsername": "root",
                "mysqlPassword": "pudongxinxu"
            },
            {
                "id": "singapore",
                "name": "Singapore",
                "domain": "wp01.charade.in",
                "folder": "/var/www/boxes",
                "mysqlUsername": "root",
                "mysqlPassword": "rZ2ARfxKIe"
            },
        ]

        self.DOMAIN = 'wp01.charade.in'
        self.FOLDER = os.path.abspath('/var/www/boxes')
        mysqlUsername = 'root'
        mysqlPassword = 'rZ2ARfxKIe'
        # self.FOLDER = os.path.abspath('/home/sparkplug/public_html/boxes')
        # mysqlUsername = 'root'
        # mysqlPassword = 'pudongxinxu'

        self.MYSQL = {
            'BIN': '/usr/bin/mysql',
            'EXEC': " -u%s -p%s --host=localhost -f -e '" % (mysqlUsername, mysqlPassword),
            'FLUSH': 'FLUSH PRIVILEGES',
            'USER_MAX_LEN': 16
        }

        self.WP = {
            'URL': 'http://wordpress.org/latest.zip',
            'SALT': 'https://api.wordpress.org/secret-key/1.1/salt/'
        }

        self.setupAbort = False
        self.setupError = ''
        self.setupMessage = 'Setting up your box, please wait ...'
        self.setupConsole = []
        self.checklist = {
            'download': 0,
            'unzip': 0,
            'configEdit': 0,
            'mysql': 0,
            'install': 0
        }

        self.emit('status', {
            'message': 'Server Connected ... '
        })
        print "Spwan Called once / again"
        self.spawn(self.job_status)

    def job_status(self):
        """
        This function sends the current box setup status to the client
        :return:
        """
        while not self.setupAbort:
            total_checks = len(self.checklist.values())
            checks = sum(self.checklist.values())

            self.emit('status', {
                'message': self.setupMessage,
                'console': self.setupConsole,
                'checks': checks,
                'total': totalChecks
            })
            gevent.sleep(1)
            if checks == totalChecks:
                self.disconnect()

        if self.setupAbort:
            self.emit('setup_failure', {
                'message': 'Sorry :( We could not setup your box ...'
            })
            self.disconnect()

    def on_test_status(self, data):
        def progressBar(blocks, blockSize, totalSize):
            percent = blocks * blockSize / float(totalSize)
            print percent

            self.emit('status', {
                'message': 'downloading ..',
                'checks': (blocks * blockSize),
                'total': totalSize
            })
            gevent.sleep(0.01)

        # Download the zip archive from the repo
        archive = urllib.urlretrieve(
            self.WP['URL'], '/home/udit/latest.zip', progressBar
        )

    def on_box_setup(self, box_data):
        """
        This function will download the wordpress
        zip file and call the unzip function if
        the download was successful.

        :param box_id: The box id is used to name the directory
        :return: Success or Failure flag
        """

        print "Starting Setup"

        self.download(box_data)     # Chains : download > unzip > editWPConfig
        self.create_db(box_data)    # Chains : create_db > create_user
        self.install_wp(box_data)
        # self.installSparkplug()

    def download(self, box_data):
        self.setupMessage = "Starting Download ..."
        # Create a directory for this installation
        dest_path = self.FOLDER + '/' + box_data['id']

        if not os.path.exists(dest_path):
            os.makedirs(dest_path)
            print "destination path :" + dest_path

        def progressBar(blocks, blockSize, totalSize):
            percent = blocks * blockSize / float(totalSize)
            print percent
            self.checklist['download'] = percent
            gevent.sleep(0.1)

        # Download the zip archive from the repo
        archive = urllib.urlretrieve(
            self.WP['URL'], '%s/latest.zip' % dest_path, progressBar
        )

        if archive:
            # The download was successful
            # Call the unzip function
            print "Download Success"
            self.setupMessage = "Download Successful, Unzipping now ..."
            self.checklist['download'] = True
            gevent.sleep(0.1)
            self.unzip(box_data, dest_path)
        else:
            # The Download was unsuccessful
            # Return a failure flag
            print 'Download Failed'

    def unzip(self, box_data, dest_path):
        """
        This function will unzip the previously downloaded
        zip file.

        :param dest_path: The dest_path passes the zip file location
        :return: Success or Failure flag
        """

        archive = zipfile.ZipFile('%s/latest.zip' % dest_path, 'r')
        archive.extractall(dest_path)
        os.unlink('%s/latest.zip' % dest_path)

        try:
            os.system('mv %s/wordpress/* %s' % (dest_path, dest_path))
            print 'Unzip Completed'
            self.setupMessage = "Unzip Completed, Editing wp-config now ..."
            self.checklist['unzip'] = True
            gevent.sleep(0.1)
            self.edit_wp_config(box_data)
        except OSError as err:
            self.setupError = err
            self.setupAbort = True

    def edit_wp_config(self, box_data):
        editConfigBreakFlag = False
        # Get salt grains from Wordpress API
        salts = urllib2.urlopen(self.WP['SALT']).read().split('\n')
        for index, salt in enumerate(salts):
            if salt != '':
                keyValues = list(salt.split(', '))
                keyValues = map( str.strip, keyValues)
                keyValues[1] = salt + '\n'
                salts[index] = keyValues
            else:
                del(salts[index])

        # put salt grains in wordpress config file
        self.setupConsole.append({
            'time': str(datetime.now().time()),
            'message': 'Editing wp-config.php with salt grains and online config.'
        })
        self.setupMessage = "Editing wp-config.php ..."

        # Get actual config file content.
        sampleConfigFilePath = '%s/%s/wp-config-sample.php' % (self.FOLDER, box_data['id'])
        configFilePath = '%s/%s/wp-config.php' % (self.FOLDER, box_data['id'])
        localConfigFilePath = '%s/%s/local-config.php' % (self.FOLDER, box_data['id'])

        try:
            configFile = open(sampleConfigFilePath, 'r')
            config = configFile.readlines()
            configFile.close()
        except IOError:
            self.setupConsole.append({
                'time': str(datetime.now().time()),
                'message': "Can't open %s" % sampleConfigFilePath
            })

        # Put salt grains in config file.
        for index, line in enumerate(config):
            for salt in salts:
                if salt[0] in line:
                    config[index] = salt[1]

        # Find DB infos and modify to use the local config instead.
        dbConfig = [
            "if(file_exists( dirname( __FILE__ ) . '/local-config.php' )) {\n",
            "   include( dirname( __FILE__ ) . '/local-config.php' );\n",
            "   define( 'WP_LOCAL_DEV', true ); // Use local plugins only\n",
            "} else {\n",
            "   define( 'DB_NAME',     'production_db'       );\n",
            "   define( 'DB_USER',     'production_user'     );\n",
            "   define( 'DB_PASSWORD', 'production_password' );\n",
            "   define( 'DB_HOST',     'production_db_host'  );\n",
            "}\n"
        ]
        beginning = '// ** MySQL settings - You can get this info from your web host ** //'
        start = 0
        ending = "define('DB_HOST', 'localhost');"
        end = 0
        for index, line in enumerate(config):
            if beginning in line:
                start = index
                pass
            if ending in line:
                end = index + 1
                pass
        config[start:end] = dbConfig

        # Saving Wordpress config file
        try:
            configFile = open(configFilePath, "w")
            configFile.writelines(config)
            configFile.close()
        except IOError:
            self.setupConsole.append({
                'time': str(datetime.now().time()),
                'message': "Can\'t save %s" % configFilePath
            })
            editConfigBreakFlag = True

        self.setupConsole.append({
            'time': str(datetime.now().time()),
            'message': "Config saved"
        })

        # Saving local db config
        self.setupConsole.append({
            'time': str(datetime.now().time()),
            'message': 'Editing local-config.php with db credientials.'
        })

        # Saving local db config
        db_name = "sparkplug_" + box_data['id']
        localDbConfig = [
            "<?php\n",
            "// ** MySQL settings - You can get this info from your web host ** //\n",
            "/** The name of the database for WordPress */\n",
            "define('DB_NAME', '%s');\n\n" % db_name,
            "/** MySQL database username */\n",
            "define('DB_USER', '%s');\n\n" % box_data['mysqlId'],
            "/** MySQL database password */\n",
            "define('DB_PASSWORD', '%s');\n\n" % box_data['mysqlPwd'],
            "/** MySQL hostname */\n",
            "define('DB_HOST', 'localhost');\n"
        ]

        try:
            localConfigFile = open(localConfigFilePath, "w")
            localConfigFile.writelines(localDbConfig)
            localConfigFile.close()
        except IOError:
            self.setupConsole.append({
                'time': str(datetime.now().time()),
                'message': "Can't save local config"
            })
            self.setupAbort = True
            editConfigBreakFlag = True

        if not editConfigBreakFlag:
            self.checklist['configEdit'] = True
            self.setupMessage = "Config edit success ..."
            gevent.sleep(0.1)
        else:
            self.setupConsole.append({
                'time': str(datetime.now().time()),
                'message': "Edit Config Failed."
            })
            self.setupAbort = True

    def create_db(self, box_data):
        """
        Create a database for wordpress.
        Will fail silently if table already exists
        """
        self.setupMessage = "Creating DB and Users ..."
        self.setupConsole.append({
            'time': str(datetime.now().time()),
            'message': 'Creating table and user in MySQL'
        })
        db_name = "sparkplug_" + box_data['id']
        self.MYSQL['CREATE_DB'] = 'CREATE DATABASE IF NOT EXISTS `%s`' % db_name
        try:
            os.system(
                self.MYSQL['BIN']
                + self.MYSQL['EXEC']
                + self.MYSQL['CREATE_DB']
                + ";'"
            )
            self.create_user(box_data)
        except OSError as err:
            self.setupConsole.append({
                'time': str(datetime.now().time()),
                'message': "Can't create DB"
            })
            self.setupAbort = True

    def create_user(self, box_data):
        """
        Create user wordpress.
        With ALL powers on table wordpress.
        Will fail silently if user already exists.
        """
        db_name = "sparkplug_" + box_data['id']
        self.MYSQL['CREATE'] = 'CREATE USER `%s`@`localhost` ' % box_data['mysqlId'] + 'IDENTIFIED BY "%s"' % box_data['mysqlPwd']
        self.MYSQL['GRANT'] = 'GRANT ALL ON `%s`.* TO `%s`@`localhost`' % (db_name, box_data['mysqlId'])

        def mysql_exec(sql='', noErr=True):
            sql = (
                self.MYSQL['BIN']
                + self.MYSQL['EXEC']
                + sql
                + ";'"
            )
            return os.system(sql)

        try:
            create = mysql_exec(self.MYSQL['CREATE'])
            grant = mysql_exec(self.MYSQL['GRANT'])
            if (create + grant) == 0:
                self.setupConsole.append({
                    'time': str(datetime.now().time()),
                    'message': "MySQL User Created"
                })
                self.checklist['mysql'] = True
        except OSError as err:
            self.setupConsole.append({
                'time': str(datetime.now().time()),
                'message': "Can't create MySQL user"
            })
            self.setupError = err
            self.setupAbort = True

    def install_wp(self, box_data):
        """
        Install wordpress.
        Not used, because this way the wordpress url will not be correct.
        """
        self.setupMessage = "Installing WordPress ..."
        self.setupConsole.append({
            'time': str(datetime.now().time()),
            'message': 'Downloading wp-cli.phar ...'
        })

        def progressBar(blocks, blockSize, totalSize):
            percent = blocks * blockSize / float(totalSize)
            print percent
            self.checklist['install'] = percent
            gevent.sleep(0.1)

        urllib.urlretrieve(
            "https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar",
            "%s/%s/wp-cli.phar" % (self.FOLDER, box_data['id']),
            progressBar
        )

        userid = box_data['mysqlId']
        args = [
            "sudo useradd -g www-data --system --no-create-home %s &&" % box_data['mysqlId'],
            "chown www-data:www-data -R %s &&" % (self.FOLDER + '/' + box_data['id']),
            # "sudo -u %s find %s -type d -exec chmod 755 {} \; &&" % (userid, self.FOLDER + '/' + box_data['id']),
            # "sudo -u %s find %s -type f -exec chmod 644 {} \; &&" % (userid, self.FOLDER + '/' + box_data['id']),
            "chmod +x %s/%s/wp-cli.phar &&" % (self.FOLDER, box_data['id']),
            "sudo -u %s %s/%s/wp-cli.phar" % (userid, self.FOLDER, box_data['id']),
            'core',
            'install',
            '--path=%s/%s' % (self.FOLDER, box_data['id']),
            '--url=%s' % box_data['id'] + '.' + self.DOMAIN,
            '--title="%s"' % box_data['name'],
            '--admin_user=%s' % box_data['username'],
            '--admin_password=%s' % box_data['password'],
            '--admin_email=%s' % box_data['email'],
        ]

        try:
            self.setupConsole.append({
                'time': str(datetime.now().time()),
                'message': 'Performing WordPress install ...'
            })
            result = call(" ".join(args), shell=True)
            print result
            if result != 0:
                self.setupAbort = True
                self.setupConsole.append({
                    'time': str(datetime.now().time()),
                    'message': "Can't install wordpress"
                })
            else:
                self.checklist['install'] = True
                self.emit('setup_complete', {
                    'message': 'Setup complete! Redirecting ...'
                })

        except OSError as err:
            self.setupConsole.append({
                'time': str(datetime.now().time()),
                'message': "Can't install wordpress"
            })
            self.setupError = err
            self.setupAbort = True
