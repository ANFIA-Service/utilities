import urllib

def login_row(lines, lookup_string): # Create config.txt to store secrets.
    for line in lines:
        if lookup_string in line:
            target_line = line.strip()
            break
    else:
        return None
    cleaned_line = target_line.strip().split(" ")[1]
    return cleaned_line

def get_login_info_from_config(config_file=""): # Get login info from config.
    """    

    Returns variables used for logins.
    -------
    How to use it:
    remember that in case you do not need to call all the variables, you can call the variables using
    only the needed variables and adding *rest for the others. Example: if you only need
    user and password, you can call user, password, *rest = get_login_info_from_config().

    """
        # if not os.path.exists(config_file):
        #     build_config()
    with open(config_file, 'r') as file:
        lines = file.readlines()
        username = login_row(lines, "username:").strip()
        password = login_row(lines, "password:").strip()
        server = login_row(lines, "server:").strip()
        database = login_row(lines, "database:").strip()
        ftp_server_address = login_row(lines, "ftp_server_address:").strip()
        ftp_user = login_row(lines, "ftp_user:").strip()
        ftp_password = login_row(lines, "ftp_password:").strip()
        tenant_id = login_row(lines, "tenant_id:").strip()
        app_id = login_row(lines, "app_id:").strip()
        secret = login_row(lines, "random_id:").strip()
        return username, password, server, database, ftp_server_address, ftp_user, ftp_password, tenant_id, app_id, secret
                
def build_connection_string(config_file):
    username, password, server, database, ftp_server_address, ftp_user, ftp_password, tenant_id, app_id, secret = get_login_info_from_config(config_file)
    app_id_encoded = urllib.parse.quote_plus(app_id)
    secret_encoded = urllib.parse.quote_plus(secret)
    connection_string = (
        f"mssql+pyodbc://{app_id_encoded}:{secret_encoded}@"
        f"{server}/{database}?"
        f"driver=ODBC+Driver+17+for+SQL+Server&"
        f"Authentication=ActiveDirectoryServicePrincipal&"
        f"TenantID={tenant_id}&"
        f"Encrypt=yes&"
        f"TrustServerCertificate=no"
    )
    return connection_string