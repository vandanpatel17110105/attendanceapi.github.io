import threading
import pandas as pd
from datetime import datetime, timedelta, date
import time
from math import ceil, exp
from random import randint
from matplotlib import pyplot as plt
from requests import get
import json
from pickle import load
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

# Date, Month, Year, Week-day, Last leave, Leaves left


def cal_formula(x, y):
	acc_u = 30
	pre_u = 30
	a = min(5 * acc_u, 5 * x)
	b = min(5 * pre_u, 5 * y)
	value = x * b

	return value


def get_employee_data():
	df = pd.read_csv('User_mapping.csv')
	df = df[
		[
			'Username', 'First Name', 'Last Name', 'Employee ID', 'Grade', 'Business Unit ID', 'Business Unit Name',
			'Organization Unit Name', 'Department Name', 'Sub Department Name', 'Location', 'City', 'Status'
		]
	]

	return df


def get_day(n):
	lst = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
	return lst[n]


def cal_acc(results):
	acc = []
	feb = []
	threshold = []
	measure = []

	temp = results[results['Actual'] == 100]
	leaves = len(temp)
	#     print(temp)
	for thr in set(temp['Leave']):
		threshold.append(thr)
		a = temp[temp['Leave'] >= thr]
		b = results[results['Leave'] >= thr]
		acc.append(100 * len(a) / len(b))
		feb.append(100 * len(a) / len(temp))
		measure.append(cal_formula(acc[-1], feb[-1]))

	result = pd.DataFrame({'Threshold': threshold, 'Accuracy': acc, 'feasible': feb, 'Measure': measure}).sort_values(
		by=['Measure'], ascending=False)
	result = result[result['Accuracy'] >= 10]
	# print(result)
	return result, leaves


def get_future_dates(n):
	tomorrow = date.today() + timedelta(1)
	lst = [tomorrow]
	for ii in range(2 * n):
		next_day = lst[-1] + timedelta(1)
		lst.append(next_day)

	future_data = pd.DataFrame({"Date": lst})

	future_data["Weekday"] = future_data["Date"].map(lambda a: a.weekday())
	future_data["Day"] = future_data["Date"].map(lambda a: a.day)
	future_data["Month"] = future_data["Date"].map(lambda a: a.month)
	future_data["Year"] = future_data["Date"].map(lambda a: a.year)
	future_data["Index"] = future_data.index

	# future_data = future_data.drop(columns=['Date'])
	future_data = future_data[future_data['Weekday'] < 5]
	future_data = future_data.head(n)
	return future_data


def predict_leaves(user_id, days, recommendations):
	print(f"starting process for Employee ID: {user_id}")
	# user_id = '24904652'
	url = "https://api10.successfactors.com/odata/v2/cust_AttendanceRegularizationdetails?" \
			"paging=cursor&$format=json&$filter=cust_Date+ge+datetime'2012-01-01T00:00:00'" \
			" and cust_Date+le+datetime'2022-02-26T00:00:00'" \
			" and cust_AttendanceRegularization_externalCode eq '" + user_id + "'"

	auth = {"Authorization": "Basic QVBJVXNlckBzdGVybGl0ZXRlOkxvZ2lucGFzc0AyMDIw"}
	param = {
		"hrmsUserName": 'APIUser@sterlitete',
		"hrmsPassword": 'Loginpass@2020'
	}

	URL = url
	at_data = []

	while True:
		try:
			URL = URL.replace("paging=cursor", "")
			r = get(url=URL, headers=auth)
			data = r.json()
			at_data += data['d']['results']

			if '__next' not in data['d'].keys():
				break

			URL = data['d']['__next']
		except Exception as e:
			print(f"API Call Error.....: {e}")
			return

	# print(len(at_data))
	json_data = at_data

	# print(len(json_data))

	Date = []
	Leave = []
	privilege_leave_types = [
		'Leave Without Pay', 'Paternity Leave', 'Casual Leave', 'Special Leave',
		'Compensatory Off Leave', 'Annual Leave', 'Privilege Leave'
	]

	for i in json_data:
		#     print(i['externalCode'], i['cust_AttendanceRegularization_effectiveStartDate'], i['cust_AbsenceReason'])
		if 'externalCode' in i and 'cust_AttendanceRegularization_externalCode' in i and 'cust_AbsenceReason' in i:

			this_date = datetime(
				int(i['externalCode'][:4]), int(i['externalCode'][4:6]), int(i['externalCode'][6:8])
			).date()

			flag = 0
			for j in privilege_leave_types:
				if j in str(i['cust_AbsenceReason']):
					flag = 1
					break

			Leave.append(flag)
			Date.append(this_date)

	data_dict = {'Date': Date, 'On_leave': Leave}
	# print("Primary DataFrame Created")
	df = pd.DataFrame(data_dict)

	df["Weekday"] = df["Date"].map(lambda a: a.weekday())
	df["Day"] = df["Date"].map(lambda a: a.day)
	df["Month"] = df["Date"].map(lambda a: a.month)
	df["Year"] = df["Date"].map(lambda a: a.year)
	df["Index"] = df.index

	df = df.drop(columns=['Date'])

	time.sleep(2)
	X = df.drop(columns=["On_leave"])
	Y = df["On_leave"]
	classifier = RandomForestClassifier(n_estimators=100, max_features="auto", random_state=42)
	classifier.fit(X, Y)

	fdf = get_future_dates(days)
	future_predict = pd.DataFrame({'Date': fdf['Date']})
	f_predict = 100 * classifier.predict_proba(fdf.drop(columns=['Date']))
	# print(f_predict)
	if len(f_predict[0]) == 1:
		future_predict['Leave'] = [0] * f_predict

	else:
		future_predict['Leave'] = [i[1] for i in f_predict]

	future_predict = future_predict.sort_values(by=['Leave', 'Date'], ascending=False)

	if recommendations > days:
		print(f"User ID: {user_id}\tError: Recommendations must be less than or equal to Days")

	Leave_list = future_predict.head(recommendations).copy()
	Leave_list["Day"] = Leave_list['Date'].map(lambda a: get_day(a.weekday()))
	Leave_list = Leave_list[['Date', 'Day', 'Leave']].sort_values(by=['Date'])
	Leave_list.set_index('Date', inplace=True)

	return Leave_list.drop(columns=['Leave'])
