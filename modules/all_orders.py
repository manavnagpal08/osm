import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta
import json
from functools import lru_cache

ON_TIME_RATE_TARGET = 95.0
DATA_QUALITY_TARGET = 98.0
COMPLETION_RATE_TARGET = 99.0

appId = 'order-processing-app-id'
try:
    firebaseConfig = json.loads(__firebase_config)
except NameError:
    firebaseConfig = {}

def generate_id():
    return ''.join(random.choices('0123456789abcdef', k=20))

class FirestoreClient:
    def __init__(self, app_id):
        self.app_id = app_id
        st.cache_data.clear()

    def fetch_orders(self):
        collection_path = f"artifacts/{self.app_id}/public/data/orders"
        st.info(f"Attempting to fetch data from Firestore collection: `{collection_path}`")

        try:
            # --- REAL FIREBASE DATA FETCHING PLACEHOLDER ---
            #
            # If using a Python SDK (e.g., google-cloud-firestore):
            # from google.cloud import firestore
            # db = firestore.Client()
            # docs = db.collection(collection_path).stream()
            # return [doc.to_dict() for doc in docs]
            #
            # --- REMOVE THIS SECTION WHEN REAL SDK IS IMPLEMENTED ---
            st.warning("Using mock data as a fallback. Implement real Firestore SDK calls in FirestoreClient.fetch_orders().")
            return self._generate_mock_orders()

        except Exception as e:
            st.error(f"Failed to connect to Firestore or fetch data: {e}. Falling back to mock data.")
            return self._generate_mock_orders()

    def _generate_mock_orders(self):
        stages = ['New', 'Processing', 'Packing', 'Storage', 'Dispatch', 'Completed', 'Cancelled']
        customer_names = ['Alpha Logistics', 'Beta Retailers', 'Gamma Services', 'Delta Supply', 'Epsilon Corp']
        
        orders_list = []
        
        for i in range(500):
            order_id = f"ORD-{1000 + i}"
            customer = random.choice(customer_names)
            stage = random.choices(stages, weights=[5, 10, 15, 10, 20, 35, 5], k=1)[0]
            
            created_at = datetime.now() - timedelta(days=random.randint(1, 60), hours=random.randint(1, 24))
            processing_at = created_at + timedelta(hours=random.randint(2, 6)) if stage != 'New' else None
            packing_at = processing_at + timedelta(hours=random.randint(1, 3)) if stage in ['Packing', 'Storage', 'Dispatch', 'Completed', 'Cancelled'] else None
            
            storage_at = packing_at + timedelta(hours=random.randint(1, 12)) if stage in ['Storage', 'Dispatch', 'Completed'] and packing_at else None
            
            dispatch_at = storage_at + timedelta(hours=random.randint(1, 12)) if stage in ['Dispatch', 'Completed'] and storage_at else None
            completed_at = dispatch_at + timedelta(hours=random.randint(48, 120)) if stage == 'Completed' and dispatch_at else None

            is_on_time = random.random() < 0.90
            
            data_quality_score = round(random.uniform(90.0, 100.0), 1)

            item_count = random.randint(1, 15)
            item_value = round(random.uniform(50.0, 500.0) * item_count, 2)
            
            order = {
                'id': generate_id(),
                'order_id': order_id,
                'customer': customer,
                'item_count': item_count,
                'total_value': item_value,
                'stage': stage,
                'is_on_time': is_on_time,
                'data_quality_score': data_quality_score,
                'created_at': created_at.isoformat(),
                'processing_started_at': processing_at.isoformat() if processing_at else None,
                'packing_completed_at': packing_at.isoformat() if packing_at else None,
                'entered_storage_at': storage_at.isoformat() if storage_at else None,
                'dispatched_at': dispatch_at.isoformat() if dispatch_at else None,
                'completed_at': completed_at.isoformat() if completed_at else None,
            }
            orders_list.append(order)
            
        return orders_list

def analyze_kpis(data_list):
    if not data_list:
        return {}

    dispatched_count = len([
        o for o in data_list 
        if o.get('dispatched_at') 
        or o.get('completed_at') 
        or o.get('stage') == 'Completed'
    ])

    completed_orders_with_time = [
        o for o in data_list 
        if o.get('completed_at') or o.get('dispatched_at')
    ]
    
    on_time_count = len([o for o in completed_orders_with_time if o.get('is_on_time')])
    
    if completed_orders_with_time:
        on_time_rate = (on_time_count / len(completed_orders_with_time)) * 100
    else:
        on_time_rate = 0.0

    quality_scores = [o.get('data_quality_score', 0) for o in data_list]
    data_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
    
    total_revenue = sum(o.get('total_value', 0) for o in data_list)

    active_wip_stages = ['New', 'Processing', 'Packing', 'Storage', 'Dispatch']
    active_wip_count = len([o for o in data_list if o.get('stage') in active_wip_stages])
    
    return {
        'on_time_rate': round(on_time_rate, 2),
        'data_quality_score': round(data_quality_score, 2),
        'total_revenue': round(total_revenue, 2),
        'dispatched_count': dispatched_count,
        'active_wip_count': active_wip_count,
    }

@lru_cache(maxsize=1)
def fetch_and_analyze_data():
    client = FirestoreClient(appId)
    try:
        data_list = client.fetch_orders()
        
        if not data_list:
            return pd.DataFrame(), [], {}

        df = pd.DataFrame(data_list)
        
        kpis = analyze_kpis(data_list)
        
        return df, data_list, kpis

    except Exception as e:
        st.error(f"Error during data fetch or analysis: {e}")
        return pd.DataFrame(), [], {}

def main():
    st.set_page_config(layout="wide")
    st.title("Production & Logistics Dashboard")
    st.markdown("Real-time overview of all current and historical orders.")

    orders_df, all_orders_list, overall_kpis = fetch_and_analyze_data()

    if orders_df.empty or not overall_kpis:
        st.warning("No orders found or data fetching failed.")
        return

    total_orders = len(all_orders_list) 
    
    on_time_rate = overall_kpis.get('on_time_rate', 0.0) 
    data_quality_score = overall_kpis.get('data_quality_score', 0.0)
    total_revenue = overall_kpis.get('total_revenue', 0.0)
    dispatched_count = overall_kpis.get('dispatched_count', 0)
    active_wip_count = overall_kpis.get('active_wip_count', 0)

    on_time_delta = f"{on_time_rate - ON_TIME_RATE_TARGET:.1f}% vs Target"
    data_quality_delta = f"{data_quality_score - DATA_QUALITY_TARGET:.1f}% vs Target"
    completion_rate = (dispatched_count / total_orders) * 100 if total_orders > 0 else 0.0
    completion_delta = f"{completion_rate - COMPLETION_RATE_TARGET:.1f}% vs Target"

    st.subheader("Key Performance Indicators (KPIs)")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            label="Total Orders", 
            value=f"{total_orders:,}",
            delta=f"Total: {total_orders:,} documents"
        )
    
    with col2:
        st.metric(
            label="Dispatch/Completion Rate", 
            value=f"{completion_rate:.1f}%",
            delta=completion_delta,
            delta_color="normal" if completion_rate >= COMPLETION_RATE_TARGET else "inverse"
        )

    with col3:
        st.metric(
            label="On-Time Delivery Rate", 
            value=f"{on_time_rate:.1f}%",
            delta=on_time_delta,
            delta_color="normal" if on_time_rate >= ON_TIME_RATE_TARGET else "inverse"
        )

    with col4:
        st.metric(
            label="Data Quality Score", 
            value=f"{data_quality_score:.1f}%",
            delta=data_quality_delta,
            delta_color="normal" if data_quality_score >= DATA_QUALITY_TARGET else "inverse"
        )
        
    with col5:
        st.metric(
            label="Total Revenue Value", 
            value=f"${total_revenue:,.0f}",
            delta=f"Total Orders Dispatched: {dispatched_count:,}"
        )
        
    st.divider()
    
    st.subheader("Work In Progress (WIP) and Inventory")
    
    orders_in_storage = orders_df[orders_df['stage'] == 'Storage']
    storage_count = len(orders_in_storage)
    storage_value = orders_in_storage['total_value'].sum()
    
    wip_col1, wip_col2, wip_col3 = st.columns(3)
    
    with wip_col1:
        st.metric(
            label="Total Active WIP",
            value=f"{active_wip_count:,}",
            delta=f"Orders not yet completed or cancelled"
        )
        
    with wip_col2:
        st.metric(
            label="Orders Currently in Storage",
            value=f"{storage_count:,}",
            delta=f"Total Value: ${storage_value:,.0f}",
        )
        
    with wip_col3:
        stage_counts = orders_df['stage'].value_counts().drop(
            labels=['Completed', 'Cancelled', 'Storage'], 
            errors='ignore'
        )
        if not stage_counts.empty:
            st.dataframe(
                stage_counts.rename("Count"), 
                use_container_width=True, 
                column_config={"stage": st.column_config.TextColumn("Stage"), "Count": st.column_config.NumberColumn("Count")},
                hide_index=False
            )
        else:
             st.markdown("No orders in 'New', 'Processing', or 'Packing' stages.")

    st.divider()
    st.subheader("All Order Details")
    
    display_columns = [
        'order_id', 'customer', 'stage', 'item_count', 'total_value', 
        'data_quality_score', 'is_on_time', 
        'created_at', 'packing_completed_at', 'entered_storage_at', 'dispatched_at', 'completed_at'
    ]
    
    for col in ['created_at', 'packing_completed_at', 'entered_storage_at', 'dispatched_at', 'completed_at']:
        orders_df[col] = pd.to_datetime(orders_df[col], errors='coerce')
        
    
    st.dataframe(
        orders_df[display_columns].sort_values(by='created_at', ascending=False),
        use_container_width=True,
        height=700,
        column_config={
            "order_id": "Order ID",
            "customer": "Customer",
            "stage": "Current Stage",
            "item_count": st.column_config.NumberColumn("Items", format="%d"),
            "total_value": st.column_config.NumberColumn("Value", format="$%d"),
            "data_quality_score": st.column_config.NumberColumn("Data Quality", format="%.1f"),
            "is_on_time": st.column_config.CheckboxColumn("On Time?"),
            "created_at": st.column_config.DatetimeColumn("Created At", format="YYYY-MM-DD HH:mm"),
            "packing_completed_at": st.column_config.DatetimeColumn("Packed At", format="HH:mm"),
            "entered_storage_at": st.column_config.DatetimeColumn("Storage At", format="HH:mm"),
            "dispatched_at": st.column_config.DatetimeColumn("Dispatched At", format="HH:mm"),
            "completed_at": st.column_config.DatetimeColumn("Completed At", format="YYYY-MM-DD"),
        }
    )

if __name__ == '__main__':
    userId = 'mock-user-id'
    
    main()
