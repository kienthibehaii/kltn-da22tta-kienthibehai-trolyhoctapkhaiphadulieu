# metrics_dashboard.py - Metrics Dashboard display functions for Streamlit UI

import streamlit as st
import pandas as pd
from typing import Dict


def display_metrics_dashboard(metrics, session_id: str):
    """
    Hiển thị dashboard metrics trong Streamlit
    
    Args:
        metrics: Performance metrics tracker instance
        session_id: Current session ID
    """
    st.markdown("---")
    st.markdown("## 📊 Performance Metrics Dashboard")
    
    # Lấy thông tin metrics
    summary = metrics.get_system_summary()
    
    # Response Time Section
    st.markdown("### ⏱️ Thời gian phản hồi")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        avg_time = summary['response_time']['average']
        st.metric("Thời gian TB", f"{avg_time:.2f}s", help="Trung bình cộng thời gian phản hồi")
    
    with col2:
        total_queries = summary['response_time']['total_queries']
        st.metric("Tổng câu hỏi", total_queries, help="Số lượng câu hỏi đã xử lý")
    
    with col3:
        if total_queries > 1:
            st.metric("Throughput", f"{total_queries/max(1, avg_time):.1f} Q/s", help="Câu hỏi per giây")
        else:
            st.metric("Throughput", "N/A")
    
    # Cache Section
    st.markdown("---")
    st.markdown("### 💾 Cache Performance")
    
    col1, col2, col3 = st.columns(3)
    
    hit_rate = summary['cache']['hit_rate']
    
    with col1:
        st.metric("Hit Rate", f"{hit_rate*100:.1f}%", 
                 delta=f"+{hit_rate*100-50:.0f}%" if hit_rate > 0.5 else f"{hit_rate*100-50:.0f}%",
                 delta_color="normal" if hit_rate > 0.5 else "off")
    
    with col2:
        st.metric("Cache Hits", summary['cache']['total_hits'])
    
    with col3:
        st.metric("Cache Misses", summary['cache']['total_misses'])
    
    # Retrieval Metrics
    if summary['retrieval']:
        st.markdown("---")
        st.markdown("### 🔍 Retrieval Quality")
        
        col1, col2, col3, col4 = st.columns(4)
        
        metrics_to_show = [
            ('precision_avg', 'Precision'),
            ('recall_avg', 'Recall'),
            ('mrr_avg', 'MRR'),
            ('ndcg_avg', 'NDCG')
        ]
        
        cols = [col1, col2, col3, col4]
        for (metric_key, metric_name), col in zip(metrics_to_show, cols):
            if metric_key in summary['retrieval']:
                value = summary['retrieval'][metric_key]
                with col:
                    st.metric(metric_name, f"{value:.3f}")
    
    # Generation Metrics
    if summary['generation']:
        st.markdown("---")
        st.markdown("### 🎯 Generation Quality")
        
        # Show available metrics
        gen_metrics = summary['generation']
        cols = st.columns(min(3, len(gen_metrics)))
        
        for i, (metric_name, value) in enumerate(list(gen_metrics.items())[:3]):
            with cols[i % len(cols)]:
                st.metric(metric_name.replace('_avg', '').upper(), f"{value:.3f}")
    
    # Citation Metrics
    if summary['citations']:
        st.markdown("---")
        st.markdown("### 📚 Citation Metrics")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if 'accuracy_avg' in summary['citations']:
                st.metric("Accuracy", f"{summary['citations']['accuracy_avg']:.2%}")
        
        with col2:
            if 'completeness_avg' in summary['citations']:
                st.metric("Completeness", f"{summary['citations']['completeness_avg']:.2%}")
        
        with col3:
            if 'relevance_avg' in summary['citations']:
                st.metric("Relevance", f"{summary['citations']['relevance_avg']:.2%}")
    
    # API Usage
    st.markdown("---")
    st.markdown("### 🔗 API Usage")
    
    col1, col2, col3 = st.columns(3)
    
    api_stats = summary['api_usage']
    
    with col1:
        st.metric("Total API Calls", api_stats['total_api_calls'])
    
    with col2:
        st.metric("Total Tokens", f"{api_stats['total_tokens']:,}")
    
    with col3:
        if api_stats['total_api_calls'] > 0:
            st.metric("Avg Tokens/Call", f"{api_stats['avg_tokens_per_call']:.0f}")
    
    # Errors
    st.markdown("---")
    st.markdown("### ❌ Error Tracking")
    
    error_count = summary['total_errors']
    total_queries = summary['response_time']['total_queries']
    error_percentage = (error_count / max(1, total_queries)) * 100 if total_queries > 0 else 0
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Total Errors", error_count,
                 delta=f"{error_percentage:.1f}% error rate" if error_percentage > 0 else "No errors")
    
    with col2:
        st.metric("Total Sessions", summary['total_sessions'])
    
    # Session Details
    st.markdown("---")
    st.markdown("### 📍 Current Session Details")
    
    if session_id in metrics.metrics['sessions']:
        session_data = metrics.metrics['sessions'][session_id]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Session Queries", session_data.get('queries', 0))
        
        with col2:
            session_times = session_data.get('response_times', [])
            if session_times:
                st.metric("Session Avg Time", f"{sum(session_times)/len(session_times):.2f}s")
            else:
                st.metric("Session Avg Time", "N/A")
        
        with col3:
            st.metric("Session Errors", session_data.get('errors', 0))
    
    # Summary box
    st.markdown("---")
    st.success(f"""
    ✅ **Metrics Summary**
    
    - Average response time: {summary['response_time']['average']:.2f}s
    - Cache hit rate: {summary['cache']['hit_rate']*100:.1f}%
    - Total queries: {summary['response_time']['total_queries']}
    - System running smoothly ✨
    """)
