from requests import Session
from datetime import date, datetime, time, timedelta


class ResponseException(Exception):
    pass


class LoginException(Exception):
    pass


class SessionException(Exception):
    pass


class NoResponseException(Exception):
    pass


class SelectContractException(Exception):
    pass


class Iber:
    __domain = "https://www.i-de.es"
    __login_url = __domain + "/consumidores/rest/loginNew/login"
    __watthourmeter_url = __domain + "/consumidores/rest/escenarioNew/obtenerMedicionOnline/24"
    __icp_status_url = __domain + "/consumidores/rest/rearmeICP/consultarEstado"
    __contracts_url = __domain + "/consumidores/rest/cto/listaCtos/"
    __contract_detail_url = __domain + "/consumidores/rest/detalleCto/detalle/"
    __contract_selection_url = __domain + "/consumidores/rest/cto/seleccion/"
    __hourly_consumption_url = __domain + "/consumidores/rest/consumoNew/obtenerDatosConsumo/fechaInicio/{:%d-%m-%Y00:00:00}/colectivo/USU/frecuencia/horas/acumular/false"
    __daily_consumption_url = __domain + "/consumidores/rest/consumoNew/obtenerDatosConsumo/fechaInicio/{:%d-%m-%Y00:00:00}/colectivo/USU/frecuencia/semanas/acumular/true"
    __monthly_maxpower_url = __domain + "/consumidores/rest/consumoNew/obtenerPotenciasMaximas/{:%d-%m-%Y00:00:00}"
    __headers = {
        'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/77.0.3865.90 Chrome/77.0.3865.90 Safari/537.36",
        'accept': "application/json; charset=utf-8",
        'content-type': "application/json; charset=utf-8",
        'cache-control': "no-cache"
    }

    def __init__(self):
        """Iber class __init__ method."""
        self.__session = None

    def login(self, user, password):
        """Creates session with your credentials"""
        self.__session = Session()
        login_data = "[\"{}\",\"{}\",null,\"Linux -\",\"PC\",\"Chrome 77.0.3865.90\",\"0\",\"\",\"s\"]".format(user,
                                                                                                               password)
        response = self.__session.request("POST", self.__login_url, data=login_data, headers=self.__headers)
        if response.status_code != 200:
            self.__session = None
            raise ResponseException("Response error, code: {}".format(response.status_code))
        json_response = response.json()
        if json_response["success"] != "true":
            self.__session = None
            raise LoginException("Login error, bad login")

    def __check_session(self):
        if not self.__session:
            raise SessionException("Session required, use login() method to obtain a session")

    def hourly_watts(self, request_date: date):
        """Returns hourly power consumption in day."""
        self.__check_session()
        response = self.__session.request("GET", self.__hourly_consumption_url.format(request_date),
                                          headers=self.__headers)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        if len(json_response['y']['data'][0]) == 0:
            raise NoResponseException
        values = []
        consumptionUnits = json_response['y']['unidadesConsumo']
        i = 0
        for data in json_response['y']['data'][0]:
            values.append(
                {
                    "from": datetime.combine(request_date, time(hour=i)),
                    "to": datetime.combine(request_date, time(hour=i)) + timedelta(hours=1),
                    "consumption": data["valor"],
                    "consumptionUnits": consumptionUnits
                }
            )
            i += 1
        return values

    def daily_watts(self, request_date: date):
        """Returns daily power consumption during week."""
        self.__check_session()
        response = self.__session.request("GET", self.__daily_consumption_url.format(request_date),
                                          headers=self.__headers)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        if len(json_response['y']['data'][0]) == 0:
            raise NoResponseException
        values = []
        consumptionUnits = json_response['y']['unidadesConsumo']
        i = 0
        for data in json_response['y']['data'][0]:
            if data is None:
                break
            values.append(
                {
                    "date": date.fromisoformat(json_response['y']['smps'][i]),
                    "consumption": data["valor"],
                    "consumptionUnits": consumptionUnits
                }
            )
            i += 1
        return values

    def monthly_max(self, request_date: date):
        """Returns daily power consumption during week."""
        self.__check_session()
        response = self.__session.request("GET", self.__monthly_maxpower_url.format(request_date),
                                          headers=self.__headers)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        if len(json_response['potMaxMens']) == 0:
            raise NoResponseException
        values = []
        i=0
        for data in json_response['potMaxMens']:
            if data is None:
                break
            values.append(
                {
                    "datetime": datetime.strptime(data["name"], '%d/%m/%Y %H:%M'),
                    "maxPower": data["y"],
                    "maxPowerLimit": json_response["areaSup"][i][1]
                }
            )
            i+=1
        return values

    def day_watts(self, request_date: date):
        """Returns daily power consumption."""
        values = [day for day in self.daily_watts(request_date) if day["date"] == request_date]
        if len(values) > 0:
            return values[0]
        else:
            raise NoResponseException

    def watthourmeter(self):
        """Returns your current power consumption."""
        self.__check_session()
        response = self.__session.request("GET", self.__watthourmeter_url, headers=self.__headers)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        return json_response['valMagnitud']

    def icpstatus(self):
        """Returns the status of your ICP."""
        self.__check_session()
        response = self.__session.request("POST", self.__icp_status_url, headers=self.__headers)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        if json_response["icp"] == "trueConectado":
            return True
        else:
            return False

    def contracts(self):
        self.__check_session()
        response = self.__session.request("GET", self.__contracts_url, headers=self.__headers)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        if json_response["success"]:
            return json_response["contratos"]

    def contract(self):
        self.__check_session()
        response = self.__session.request("GET", self.__contract_detail_url, headers=self.__headers)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        return response.json()

    def contractselect(self, id):
        self.__check_session()
        response = self.__session.request("GET", self.__contract_selection_url + id, headers=self.__headers)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        if not json_response["success"]:
            raise SelectContractException
