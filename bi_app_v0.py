#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import streamlit as st
import os
import pandas as pd
from langchain.chat_models import ChatOpenAI
from langchain.agents import create_pandas_dataframe_agent
from langchain.callbacks import get_openai_callback
import gspread
import openai
import numpy as np
import json

# API Keys (consider using environment variables or a secure method to store these)
openai.api_key = st.secrets["chatkey"]
json_creds = st.secrets["gspread_creds"]
gc = gspread.service_account_from_dict(json_creds)

# Sidebar capabilities
st.sidebar.header("Capabilities")
choice = st.sidebar.selectbox("", ["Main", "Help Writing a Query"])

# Function to get data from Google Sheet
def get_google_sheet_data(workbook_name, sheet_name):
    sh = gc.open(workbook_name)
    google_sheet = sh.worksheet(sheet_name).get_all_values()
    headers = google_sheet[0]
    df = pd.DataFrame(google_sheet[1:], columns=headers)
    return df

df = get_google_sheet_data('BI Test', 'Sheet1')

df['Products Sold'] = df['Products Sold'].astype(str).str.replace(',', '').astype(int)
df['Transactions'] = df['Transactions'].astype(str).str.replace(',', '').astype(int)
df['GMV'] = df['GMV'].astype(str).str.replace(',', '').astype(float)
df['Quantity'] = df['Quantity'].astype(str).str.replace(',', '').astype(int)
df['Refund Amount'] = df['Refund Amount'].astype(str).replace('', np.nan).str.replace(',', '').astype(float)


if choice == "Main":
    # Centered title in the main content area
    st.markdown("<h1 style='text-align: center;'>Welcome to <span style='color: #39FF14;'>Wish <b>Business Intelligence AI</span></h1>", unsafe_allow_html=True)
    st.write("""
    This textbox below has AI capabilities which allow you to ask and converse with the most recent BI data.
    To see what other functionalities Wish Business Intelligence AI has, click on the menu on the left-hand side.
    """)

    with st.expander("Dataset Information", expanded=False):
        st.markdown(f"**Date Range:** 6/26/2023 - 8/21/2023")
        st.markdown("**Dimensions:** Week, Buyer Region, Client, Merchant Country")
        st.markdown("**Data:** Refunded Amount, Quantity, GMV, Transactions, Products Sold")
        st.markdown("**Dataset:** [Google Sheet](https://docs.google.com/spreadsheets/d/1PF2hMXYjOWPV3ZrvehIR5OO0Sn5DZsHnvEXvfPH0dIA/edit?usp=sharing)")

    # Main text box to accept user input in the main content area
    user_input = st.text_area('Enter your question:',placeholder='How many transactions were made the week of August 7th 2023 by each Client?')

    submit_button = st.button('Submit')

    if submit_button and user_input:
        chat = ChatOpenAI(model_name = "gpt-3.5-turbo-0301", temperature = 0.0)
        agent = create_pandas_dataframe_agent(chat, df)
        with get_openai_callback() as cb:
            result = agent.run(user_input)
            st.write(result)
            st.markdown("<hr/>", unsafe_allow_html=True)
            cb_str = str(cb)
            lines = cb_str.split('\n')
            tokens_used_line = lines[0]
            prompt_tokens_line = lines[1]
            completion_tokens_line = lines[2]
            total_cost_line = lines[4]

            tokens_used = int(tokens_used_line.split(": ")[1])
            prompt_tokens = int(prompt_tokens_line.split(": ")[1])
            completion_tokens = int(completion_tokens_line.split(": ")[1])
            total_cost = total_cost_line.split(": ")[1]

            st.write('Cost Information:')
            st.write(f'Prompt Tokens: {prompt_tokens}')
            st.write(f'Completion Tokens: {completion_tokens}')
            st.write(f'Total Tokens: {tokens_used}')
            st.write(f'USD Cost: {total_cost}')

elif choice == 'Help Writing a Query':
    st.markdown("<h1 style='text-align: center;'>What data are you querying for?</h1>", unsafe_allow_html=True)

    st.write("""
    In the box below, have Wish AI write a query for you.
    """)

    main_query = st.text_area(label = '',value='', placeholder='How many transactions were made in October 2023? Which countries had the highest GMV last week?')
    submit_button = st.button('Submit')

    content = "you are a data scientist for a worldwide e-commerce company. you have access to two tables, core_data.fct_transaction_variations which holds transaction information on the order_id level for every day. the other table is core_data.fct_dau_w_bots that is on the user_id level for every day. The transaction table has the following columns, user_id, product_id, merchant_id, dt (YYY-MM-DD), transaction_id,order_id,gmv_variation,shipping_country (two letter code) and client. The other table has dt (YYYY-MM-DD), user_id, user_type, client, country_code (two letter code), num_impressions, num_clicks, num_a2c_actions. You will be asked questions on how to write presto sql queries. Ensure that your queries do not end with a semicolon. If you're not sure, say Not sure how to do that right now."

    if submit_button and main_query:
        completion = openai.ChatCompletion.create(model = "gpt-3.5-turbo", messages = [
                {"role":"user","content":content},
                {"role":"assistant","content":"OK, I’m ready."},
        #everything below are examples. We can add more, but it will cost.
                {"role":"user","content": "Retrieve the total number of transactions for the date YYYY-MM-DD."},
                {"role":"assistant","content":"select count(distinct transaction_id) as transactions from core_data.fct_transaction_variations where dt = 'YYYY-MM-DD'"},
                {"role":"user","content": "Calculate the average GMV for the country with the country code \"US\" on the date 2023-03-10."},
                {"role":"assistant","content":"with temp as (select user_id,sum(gmv_variation) as gmv from core_data.fct_transaction_variations where shipping_country = \"US\"and dt = '2023-03-10' group by 1) select avg(gmv) as avg_gmv from temp"},
                {"role":"user","content": "Number of user_ids that had more than 100,000 impressions by client for the month of January 2023."},
                {"role":"assistant","content":"select client, count(distinct user_id) as user_ids from core_data.fct_dau_w_bots where date_trunc('month',date(dt)) = date('2023-01-01') group by 1having sum(num_impressions) > 100000"},
                {"role":"user","content": "Get the client that generated the highest number of Add-to-Cart actions on the date YYYY-MM-DD."},
                {"role":"assistant","content":"with temp as (select client,sum(num_a2c_actions) as a2c from core_data.fct_dau_w_bots where dt = YYYY-MM-DD group by 1 order by 1) select * from temp limit 1"},
                {"role":"user","content": "Calculate the conversion rate by country for the week of August 7, 2023"},
                {"role":"assistant","content":"with txns as (select date_trunc('week',date(dt)) as week,shipping_country,count(distinct user_id) as buyers from core_data.fct_transaction_variations where date_trunc('week',date(dt)) = date('2023-08-07') group by 1,2), dau as (select date_trunc('week',date(dt)) as week,country_code,count(distinct user_id) as dau from core_data.fct_dau_w_bots where date_trunc('week',date(dt)) = date('2023-08-07') group by 1,2) select country_code,buyers*1.00000/dau from dau a left join txns b on a.week = b.week and b.shipping_country = a.country_code"},
                {"role":"user","content": "GMV by merchant_id and country for last week"},
                {"role":"assistant","content":"select merchant_id,shipping_country,sum(gmv_variation) as gmv from core_data.fct_transaction_variations where date_trunc('week',date(dt)) = date_trunc('week',current_date - interval '7' day) group by 1,2 "},
                {"role":"user","content": "How many distinct users did we have in July 2023? Break it down by client and country"},
                {"role":"assistant","content":"select client,country_code,count(distinct user_id) as users from core_data.fct_dau_w_bots where date_trunc(‘month’,date(dt)) = date(‘2023-07-01’) group by 1,2"},
                {"role":"user","content": "Number of transactions on October 2nd 2021?"},
                {"role":"assistant","content":"select count(distinct transaction_id) as transactions from core_data.fct_transaction_variations where dt = '2021-10-02'"},
                #this line ensure we use the prompt above
                {"role":"user","content":main_query}],
                #0 creativity. Just do what we told you to.
                temperature = 0.0

        )


        reply_content = completion.choices[0].message.content

        st.write(reply_content)
        st.markdown("<hr/>", unsafe_allow_html=True)
        usage = completion['usage']
        prompt_tokens = usage['prompt_tokens']
        completion_tokens = usage['completion_tokens']
        total_tokens = usage['total_tokens']

        # Calculate USD cost based on token usage
        input_token_cost = (0.0015/1000)
        output_token_cost = (0.002/1000)# Cost per token (check OpenAI's pricing)
        usd_cost = "{:.8f}".format(((prompt_tokens*input_token_cost) + (completion_tokens*output_token_cost)))

        st.write('Cost Information:')
        st.write(f'Prompt Tokens: {prompt_tokens}')
        st.write(f'Completion Tokens: {completion_tokens}')
        st.write(f'Total Tokens: {total_tokens}')
        st.write(f'USD Cost: {usd_cost}')
