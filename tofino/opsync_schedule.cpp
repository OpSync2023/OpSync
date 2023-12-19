/*
 * Control Plane program for test tofino2 pktgen
 * Compile using following command : make 
 * To Execute, Run: ./run.sh
 *
 */
#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>
#include <stdint.h>
#include <sched.h>
#include <string.h>
#include <time.h>
#include <assert.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <pthread.h>
#include <unistd.h>
#include <pcap.h>
#include <arpa/inet.h>

#include <bf_rt/bf_rt.hpp>

//#include "pktgen.cpp"
using namespace std;

#define ALL_PIPES 0xffff

#ifdef __cplusplus
extern "C"
{
#endif
#include <bf_switchd/bf_switchd.h>
#include <pipe_mgr/pktgen_intf.h>
#include <tofino/pdfixed/pd_conn_mgr.h>
#include <tofino/pdfixed/pd_tm.h>
#include <tofino/pdfixed/pd_common.h>
#ifdef __cplusplus
}
#endif

#define THRIFT_PORT_NUM 7777
#define SIZE 100
#define TOR_NUM 192

p4_pd_sess_hdl_t sess_hdl;
int switchid = 0;
uint64_t pkt_cnt;
uint64_t batch_cnt;
struct p4_pd_pktgen_app_cfg_tof2 app_cfg;

const bfrt::BfRtInfo *bfrtInfo = nullptr;

char * buf;

void init_bf_switchd(const char* progname) {
	bf_switchd_context_t *switchd_main_ctx = NULL;
	char *install_dir;	
	char target_conf_file[100];
	bf_status_t bf_status;
	install_dir = getenv("SDE_INSTALL");
	sprintf(target_conf_file, "%s/share/p4/targets/tofino2/%s.conf", install_dir, progname);

	/* Allocate memory to hold switchd configuration and state */
	if ((switchd_main_ctx = (bf_switchd_context_t *)calloc(1, sizeof(bf_switchd_context_t))) == NULL) {
		printf("ERROR: Failed to allocate memory for switchd context\n");
		return;
	}

	memset(switchd_main_ctx, 0, sizeof(bf_switchd_context_t));
	switchd_main_ctx->install_dir = install_dir;
	switchd_main_ctx->conf_file = target_conf_file;
	switchd_main_ctx->skip_p4 = false;
	switchd_main_ctx->skip_port_add = false;
	switchd_main_ctx->running_in_background = true;
	switchd_main_ctx->dev_sts_thread = true;
	switchd_main_ctx->dev_sts_port = THRIFT_PORT_NUM;

	bf_status = bf_switchd_lib_init(switchd_main_ctx);
	printf("Initialized bf_switchd, status = %d\n", bf_status);
}

void getSwitchName () {
	char switchName[25];
	FILE *f = fopen("/etc/hostname", "r");
	fscanf(f, "%s", switchName);
	if (strcmp(switchName, "switch4-jupiter") == 0) {
		switchid = 4;
	}
	else if (strcmp(switchName, "switch6-uranus") == 0) {
		switchid = 6;
	}
	else if (strcmp(switchName, "switch7-neptune") == 0) {
		switchid = 7;
	}
	printf("Detected running on switch %d\n", switchid);
}

void init_tables() {
	char cwd[512];
	char bfrtcommand[512];
	if (getcwd(cwd, sizeof(cwd)) != NULL) {
		printf("Current working dir: %s\n", cwd);
	}
	//printf("Current WD:%s\n", cwd);
	//sprintf(bfrtcommand, "bfshell -b %s/setup.py", cwd);
	sprintf(bfrtcommand, "bfshell -b /home/p4/path/Opsync/opsync_schedule/setup.py");
	//sprintf(bfrtcommand, "bfshell -b /home/p4/path/Opsync/opsync_schedule/setup_profile.py");
	//sprintf(bfrtcommand, "bfshell -b /home/p4/path/Opsync/opsync_schedule/setup_failure.py");
	//sprintf(bfrtcommand, "bfshell -b /home/p4/path/Opsync/opsync_schedule/setup_toy_example.py");
	printf("%s\n", bfrtcommand);
	system(bfrtcommand);
}

void write_buf(int dptp_type) {
    buf = (char *)malloc(SIZE);

	memset(buf,0,SIZE);

	buf[0] = 0x99;
	buf[0xc] = 0x08; // ether_type = IPv4
	buf[0xd] = 0x00; // ether_type = IPv4
	buf[0xe] = 0x45; // IP version = 4

	buf[0x10] = 0x00; // Total Length = 94
	buf[0x11] = 0x5e; // Total Length = 94

	buf[0x14] = 0x00; // flag = 0
	buf[0x15] = 0x00; // frag = 0

	buf[0x16] = 0x10; //ttl
	buf[0x17] = 0x11; //udp
	
	buf[0x23] = 0xdd; //src_port;
	buf[0x25] = 0xdd; //dst_port;
	buf[0x27] = 0x30; //udp length

	//buf[0x2a] = dptp_type; //dptp_type;
	buf[0x2a] = 0; //dptp_type;
	buf[0x2b] = dptp_type; //INIT=0x00, REQ=0x01

}

void set_pktgen(p4_pd_dev_target_t pd_dev_tgt) {

	p4_pd_status_t pd_status;
	for(int pipe_id = 0; pipe_id < 1; pipe_id++){
    	pd_status = p4_pd_pktgen_enable(sess_hdl, 0, 6 + 128 * pipe_id);
		if (pd_status != 0) {
			printf("Failed to enable pktgen status = %d!!\n", pd_status);
			return;
		}

		bool enable;
		p4_pd_pktgen_enable_state_get(sess_hdl, 0, 6 + 128 * pipe_id, &enable);
		printf("port %d pktgen enable state %d\n", 6 + 128 * pipe_id, enable);
	}

    app_cfg.trigger_type = PD_PKTGEN_TRIGGER_TIMER_PERIODIC;
	//app_cfg.trigger_type = PD_PKTGEN_TRIGGER_TIMER_ONE_SHOT;
	//app_cfg.trigger_type = PD_PKTGEN_TRIGGER_DPRSR;
    app_cfg.batch_count = (3 * TOR_NUM) - 1;//2 * TOR_NUM-1;
    app_cfg.packets_per_batch = TOR_NUM-1;//999;
    app_cfg.timer_nanosec = 1000 * 1000 * 3;//4294967295;
    app_cfg.ibg = 50;
    app_cfg.ibg_jitter = 0;
    app_cfg.ipg = 50;
    app_cfg.ipg_jitter = 0;
    app_cfg.source_port = 6;
	app_cfg.assigned_chnl_id = 6;
    app_cfg.increment_source_port = false;
    app_cfg.pkt_buffer_offset = 0;
    app_cfg.length = SIZE;

	buf = (char *)malloc(SIZE);
	write_buf(0x10);
	pd_status = p4_pd_pktgen_write_pkt_buffer(sess_hdl, pd_dev_tgt, 0, 64, (uint8_t*)buf);
    
    if (pd_status != 0) {
        printf("Pktgen: Writing Packet buffer failed!\n");
        return;
    }

    p4_pd_pktgen_cfg_app_tof2(sess_hdl, pd_dev_tgt, (int)1, app_cfg);
    p4_pd_pktgen_app_enable(sess_hdl, pd_dev_tgt, 1);

	p4_pd_pktgen_get_pkt_counter(sess_hdl, pd_dev_tgt, 1, &pkt_cnt);
	p4_pd_pktgen_get_batch_counter(sess_hdl, pd_dev_tgt, 1, &batch_cnt);
    printf("app=%lu, pkt_cnt=%lu, batch_cnt=%lu\n", 1, pkt_cnt, batch_cnt);
}


int main(int argc, char **argv) {
	const char * p4progname = "opsync_schedule";
	bf_dev_target_t dev_tgt;
	p4_pd_dev_target_t pd_dev_tgt;

	// Initialize the device id and pipelines to be used for DPTP
    dev_tgt.device_id = 0;
    dev_tgt.dev_pipe_id = ALL_PIPES;

	pd_dev_tgt.device_id = 0;
	pd_dev_tgt.dev_pipe_id = ALL_PIPES;

	// Start the BF Switchd
	init_bf_switchd(p4progname);

	getSwitchName();
	printf("Starting  Switch..\n");
	sleep(5);
	//if(switchid == 4) {
		set_pktgen(pd_dev_tgt);
		/*
		for (i = 0; i < interval_size; i++) {
			set_pktgen(pd_dev_tgt, intervals[i]);
			sleep(2 * intervals[i]);
			system("bfshell -b /home/p4/path/dptp_tx_multi_hop/measure/read_drift_json.py");
			p4_pd_pktgen_app_disable(sess_hdl, pd_dev_tgt, 1);
		}
		*/
	//}
	init_tables();
	//system("bfshell -b /home/p4/path/measure_dataplane_pktgen/read_rst.py");
	
	system("bfshell");

	return 0;
}