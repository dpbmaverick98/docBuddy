#!/usr/bin/env python3
"""
🚀 DocsBuddy Comprehensive Optimization Dashboard
Real-time monitoring, performance analysis, and system control
"""
import os
import sys
import time
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import curses
import argparse

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from services.monitoring import get_metrics, get_cache_stats
    from services.config import get_config
    from services.journey_generator import JourneyGenerator
    from services.cache_manager import get_cache_manager
    from services.optimized_client import get_connection_pool
except ImportError as e:
    print(f"❌ Cannot import backend modules: {e}")
    sys.exit(1)


class OptimizationDashboard:
    """Comprehensive dashboard for monitoring DocsBuddy optimization"""
    
    def __init__(self):
        self.running = True
        self.refresh_interval = 2  # seconds
        self.performance_data = []
    
    def get_system_status(self):
        """Get overall system health status"""
        try:
            config = get_config()
            metrics = get_metrics()
            cache_stats = get_cache_stats()
            
            if metrics:
                current = metrics.get_current_metrics()
                
                # Determine health status
                health_score = 100
                issues = []
                
                if current.cache_hit_rate < 30:
                    health_score -= 20
                    issues.append("Low cache hit rate")
                if current.average_response_time > 10:
                    health_score -= 15
                    issues.append("Slow response times")
                if current.active_connections > 15:
                    health_score -= 10
                    issues.append("High concurrency")
                if current.total_cost_usd > 50:
                    health_score -= 10
                    issues.append("High costs")
                
                status_emoji = "🟢" if health_score >= 80 else "🟡" if health_score >= 60 else "🔴"
                status_text = "Excellent" if health_score >= 80 else "Good" if health_score >= 60 else "Poor"
                
                return {
                    'status': f"{status_emoji} {status_text}",
                    'health_score': health_score,
                    'issues': issues,
                    'uptime': self._get_uptime()
                }
            return {'status': '❌ No Metrics Available', 'health_score': 0, 'issues': ['Metrics not available']}
        except Exception as e:
            return {'status': f'❌ Error: {str(e)}', 'health_score': 0, 'issues': [str(e)]}
    
    def _get_uptime(self):
        """Calculate system uptime (mock for now)"""
        return "24h 15m (since last restart)"
    
    def get_performance_metrics(self):
        """Get detailed performance metrics"""
        try:
            metrics = get_metrics()
            if not metrics:
                return None
            
            current = metrics.get_current_metrics()
            cache_stats = get_cache_stats()
            
            return {
                'total_requests': current.total_requests,
                'successful_requests': current.successful_requests,
                'failed_requests': current.failed_requests,
                'success_rate': (current.successful_requests / current.total_requests * 100) if current.total_requests > 0 else 0,
                'average_response_time': current.average_response_time,
                'cache_hit_rate': current.cache_hit_rate,
                'total_cost_usd': current.total_cost_usd,
                'cost_per_journey': current.total_cost_usd / max(current.total_requests, 1),
                'active_connections': current.active_connections,
                'total_tokens': current.total_tokens,
                'requests_per_minute': self._calculate_rpm(),
                'cost_per_hour': self._calculate_cph(current)
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _calculate_rpm(self):
        """Calculate requests per minute"""
        try:
            metrics = get_metrics()
            if metrics and hasattr(metrics, 'request_metrics'):
                recent_requests = [r for r in metrics.request_metrics 
                               if r.start_time > time.time() - 60]  # Last minute
                return len(recent_requests)
        except:
            pass
        return 0
    
    def _calculate_cph(self, current):
        """Calculate cost per hour"""
        try:
            # Get requests from last hour
            metrics = get_metrics()
            if metrics and hasattr(metrics, 'request_metrics'):
                recent_requests = [r for r in metrics.request_metrics 
                               if r.start_time > time.time() - 3600]  # Last hour
                if recent_requests:
                    hour_cost = sum(r.api_calls[0].get('cost_usd', 0) for r in recent_requests for r.api_calls)
                    return hour_cost
        except:
            pass
        return current.total_cost_usd  # Fallback
    
    def get_cache_analysis(self):
        """Get detailed cache performance analysis"""
        try:
            cache_stats = get_cache_stats()
            if not cache_stats:
                return None
            
            analysis = {}
            for cache_type, stats in cache_stats.items():
                if stats['size'] > 0:
                    hit_rate = (stats['hits'] / (stats['hits'] + stats['misses']) * 100) if (stats['hits'] + stats['misses']) > 0 else 0
                    efficiency = min((stats['size'] / stats['max_size'] * 100), 100)
                    
                    analysis[cache_type] = {
                        'hit_rate': hit_rate,
                        'efficiency': efficiency,
                        'total_entries': stats['size'],
                        'max_size': stats['max_size'],
                        'memory_usage': 'High' if efficiency > 80 else 'Medium' if efficiency > 50 else 'Low',
                        'performance': '🟢' if hit_rate > 70 else '🟡' if hit_rate > 40 else '🔴'
                    }
            
            return analysis
        except Exception as e:
            return {'error': str(e)}
    
    def get_optimization_settings(self):
        """Get current optimization configuration"""
        try:
            config = get_config()
            return {
                'cache': {
                    'embeddings_size': config.cache.embeddings_size,
                    'rag_size': config.cache.rag_size,
                    'llm_size': config.cache.llm_size,
                    'intent_size': config.cache.intent_size,
                    'summary_size': config.cache.summary_size
                },
                'connections': {
                    'max_connections': config.connections.max_connections,
                    'timeout': config.connections.connection_timeout,
                    'max_retries': config.connections.max_retries
                },
                'llm': {
                    'max_context_tokens': config.llm.max_context_tokens,
                    'journey_temp': config.llm.journey_generation_temp,
                    'summary_temp': config.llm.summarization_temp,
                    'default_model': config.llm.default_model
                },
                'rag': {
                    'use_expansion': config.rag.use_query_expansion,
                    'use_rerank': config.rag.use_rerank,
                    'use_compression': config.rag.use_compression,
                    'default_top_k': config.rag.default_top_k
                },
                'performance': {
                    'max_concurrent': config.performance.max_concurrent_requests,
                    'batch_processing': config.performance.batch_processing_enabled,
                    'metrics_enabled': config.performance.enable_metrics
                }
            }
        except Exception as e:
            return {'error': str(e)}
    
    def run_performance_test(self):
        """Run a performance test to validate optimizations"""
        try:
            print("🧪 Running Performance Test...")
            start_time = time.time()
            
            generator = JourneyGenerator(use_rag=True, temperature=0.7)
            
            # Test 1: Journey generation
            result1 = generator.generate_journey("test authentication", max_steps=3)
            time1 = time.time() - start_time
            
            # Test 2: Same query (should hit cache)
            start_time = time.time()
            result2 = generator.generate_journey("test authentication", max_steps=3)
            time2 = time.time() - start_time
            
            # Test 3: Different query
            start_time = time.time()
            result3 = generator.generate_journey("set up oauth", max_steps=3)
            time3 = time.time() - start_time
            
            return {
                'test1': {'time': time1, 'cached': False, 'success': 'error' not in result1},
                'test2': {'time': time2, 'cached': time2 < time1 * 0.5, 'success': 'error' not in result2},
                'test3': {'time': time3, 'cached': False, 'success': 'error' not in result3},
                'cache_speedup': ((time1 - time2) / time1 * 100) if time1 > 0 else 0,
                'overall_performance': '🟢 Excellent' if time1 < 5 else '🟡 Good' if time1 < 10 else '🔴 Needs attention'
            }
        except Exception as e:
            return {'error': str(e)}
    
    def generate_report(self):
        """Generate comprehensive optimization report"""
        try:
            system_status = self.get_system_status()
            performance = self.get_performance_metrics()
            cache_analysis = self.get_cache_analysis()
            settings = self.get_optimization_settings()
            test_results = self.run_performance_test()
            
            report = {
                'timestamp': datetime.now().isoformat(),
                'system_status': system_status,
                'performance_metrics': performance,
                'cache_analysis': cache_analysis,
                'settings': settings,
                'performance_test': test_results,
                'recommendations': self._generate_recommendations(system_status, performance, cache_analysis)
            }
            
            # Save report
            report_file = f"optimization_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            return report, report_file
        except Exception as e:
            return {'error': str(e)}, None
    
    def _generate_recommendations(self, status, performance, cache_analysis):
        """Generate optimization recommendations"""
        recommendations = []
        
        if performance:
            if performance.get('cache_hit_rate', 0) < 40:
                recommendations.append({
                    'priority': 'High',
                    'category': 'Cache',
                    'issue': 'Low cache hit rate',
                    'solution': 'Increase cache sizes or adjust TTL settings'
                })
            
            if performance.get('average_response_time', 0) > 10:
                recommendations.append({
                    'priority': 'High',
                    'category': 'Performance',
                    'issue': 'Slow response times',
                    'solution': 'Check API latency or enable more aggressive caching'
                })
            
            if performance.get('active_connections', 0) > 15:
                recommendations.append({
                    'priority': 'Medium',
                    'category': 'Concurrency',
                    'issue': 'High concurrent requests',
                    'solution': 'Increase connection pool size or implement rate limiting'
                })
        
        if cache_analysis:
            for cache_type, stats in cache_analysis.items():
                if isinstance(stats, dict) and stats.get('efficiency', 0) > 90:
                    recommendations.append({
                        'priority': 'Medium',
                        'category': 'Memory',
                        'issue': f'{cache_type} cache nearly full',
                        'solution': f'Increase {cache_type} cache max size or reduce TTL'
                    })
        
        return recommendations
    
    def display_dashboard_curses(self, stdscr):
        """Display real-time dashboard using curses"""
        curses.curs_set(0)
        
        while self.running:
            stdscr.clear()
            stdscr.addstr(0, 0, "🚀 DocsBuddy Optimization Dashboard")
            stdscr.addstr(1, 0, "=" * 50)
            
            # System status
            status = self.get_system_status()
            stdscr.addstr(3, 0, f"System Status: {status['status']}")
            stdscr.addstr(4, 0, f"Health Score: {status['health_score']}/100")
            stdscr.addstr(5, 0, f"Uptime: {status['uptime']}")
            
            # Performance metrics
            perf = self.get_performance_metrics()
            if perf:
                stdscr.addstr(7, 0, "📊 Performance:")
                stdscr.addstr(8, 2, f"Cache Hit Rate: {perf.get('cache_hit_rate', 0):.1f}%")
                stdscr.addstr(9, 2, f"Avg Response: {perf.get('average_response_time', 0):.3f}s")
                stdscr.addstr(10, 2, f"Active Requests: {perf.get('active_connections', 0)}")
                stdscr.addstr(11, 2, f"Total Cost: ${perf.get('total_cost_usd', 0):.2f}")
            
            # Cache analysis
            cache_stats = self.get_cache_analysis()
            if cache_stats:
                stdscr.addstr(13, 0, "🧠 Cache Analysis:")
                y_pos = 14
                for cache_type, stats in list(cache_stats.items())[:3]:  # Show first 3
                    if isinstance(stats, dict):
                        status_emoji = stats.get('performance', '❓')
                        stdscr.addstr(y_pos, 0, f"{cache_type}: {status_emoji} {stats.get('hit_rate', 0):.1f}%")
                        y_pos += 1
            
            # Commands
            stdscr.addstr(20, 0, "🎮 Commands:")
            stdscr.addstr(21, 2, "[r] Refresh | [t] Test Performance | [q] Quit")
            
            # Refresh display
            stdscr.refresh()
            
            # Handle input
            try:
                key = stdscr.getch()
                if key == ord('q'):
                    self.running = False
                elif key == ord('r'):
                    pass  # Refresh is automatic
                elif key == ord('t'):
                    self.run_performance_test()
            except:
                self.running = False
        
        curses.endwin()


def display_simple_dashboard():
    """Display simple text dashboard"""
    dashboard = OptimizationDashboard()
    
    while dashboard.running:
        os.system('clear')
        print("🚀 DocsBuddy Optimization Dashboard")
        print("=" * 50)
        
        # System status
        status = dashboard.get_system_status()
        print(f"System Status: {status['status']}")
        print(f"Health Score: {status['health_score']}/100")
        print(f"Issues: {', '.join(status['issues'])}")
        
        # Performance
        perf = dashboard.get_performance_metrics()
        if perf:
            print("\n📊 Performance Metrics:")
            print(f"  Total Requests: {perf.get('total_requests', 0)}")
            print(f"  Cache Hit Rate: {perf.get('cache_hit_rate', 0):.1f}%")
            print(f"  Avg Response: {perf.get('average_response_time', 0):.3f}s")
            print(f"  Total Cost: ${perf.get('total_cost_usd', 0):.2f}")
            print(f"  Active Connections: {perf.get('active_connections', 0)}")
        
        # Cache analysis
        cache_stats = dashboard.get_cache_analysis()
        if cache_stats:
            print("\n🧠 Cache Performance:")
            for cache_type, stats in cache_stats.items():
                if isinstance(stats, dict):
                    print(f"  {cache_type.title()}: {stats.get('performance', '❓')} {stats.get('hit_rate', 0):.1f}%")
        
        print("\n🎮 Commands: [r] Refresh | [t] Test | [s] Settings | [q] Quit")
        
        time.sleep(2)


def main():
    """Main dashboard application"""
    parser = argparse.ArgumentParser(description='DocsBuddy Optimization Dashboard')
    parser.add_argument('--mode', choices=['simple', 'live', 'report', 'test'], 
                       default='simple', help='Dashboard mode')
    parser.add_argument('--output', help='Output file for report mode')
    args = parser.parse_args()
    
    dashboard = OptimizationDashboard()
    
    if args.mode == 'simple':
        print("🚀 Starting Simple Dashboard Mode...")
        while dashboard.running:
            try:
                display_simple_dashboard()
            except KeyboardInterrupt:
                print("\n👋 Dashboard stopped")
                break
    
    elif args.mode == 'live':
        try:
            print("🚀 Starting Live Dashboard Mode...")
            stdscr = curses.initscr()
            dashboard.display_dashboard_curses(stdscr)
        except KeyboardInterrupt:
            print("\n👋 Live dashboard stopped")
        except Exception as e:
            print(f"❌ Live dashboard error: {e}")
    
    elif args.mode == 'report':
        print("🚀 Generating Optimization Report...")
        report, report_file = dashboard.generate_report()
        
        if report_file:
            print(f"✅ Report saved to: {report_file}")
        
        # Display summary
        if 'error' not in report:
            print("\n📊 Report Summary:")
            print(f"System Health: {report['system_status']['status']}")
            print(f"Performance: 🟢 Excellent" if report['system_status']['health_score'] >= 80 else "🟡 Good" if report['system_status']['health_score'] >= 60 else "🔴 Poor")
            
            recommendations = report.get('recommendations', [])
            if recommendations:
                print(f"\n⚠️ {len(recommendations)} Recommendations:")
                for rec in recommendations:
                    print(f"  {rec['priority']}: {rec['issue']} - {rec['solution']}")
        else:
            print(f"❌ Report generation failed: {report.get('error')}")
    
    elif args.mode == 'test':
        print("🧪 Running Performance Test...")
        results = dashboard.run_performance_test()
        
        if 'error' not in results:
            print("\n📊 Test Results:")
            print(f"Test 1 (cold cache): {results['test1']['time']:.3f}s")
            print(f"Test 2 (warm cache): {results['test2']['time']:.3f}s ({'✅ Hit' if results['test2']['cached'] else '❌ Miss'})")
            print(f"Test 3 (different): {results['test3']['time']:.3f}s")
            print(f"Cache Speedup: {results.get('cache_speedup', 0):.1f}%")
            print(f"Overall Performance: {results.get('overall_performance', '❓')}")
        else:
            print(f"❌ Test failed: {results.get('error')}")


if __name__ == "__main__":
    main()