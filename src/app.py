from fbprophet import Prophet
import pandas as pd

with open("../notebooks/data.csv",'r') as f:
    with open("updated_test.csv",'w') as f1:
        next(f) # skip header line
        for line in f:
            f1.write(line)

df = pd.read_csv('updated_test.csv', sep=';')

df = df[['Date', 'Closingprice']]
df.columns = ['ds', 'y']

df['y'] = df.y.str.replace(',','')
df['y'] = df['y'].astype(float)

df = df.iloc[::-1]
df = df.reset_index(drop=True)


m = Prophet(interval_width=0.95)
m.fit(df)

future = m.make_future_dataframe(periods=1)

forecast = m.predict(future)

print(forecast.yhat[-1:].values[0])


print('everything OK!')