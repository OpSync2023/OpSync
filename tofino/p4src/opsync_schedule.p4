#include <core.p4>
#if __TARGET_TOFINO__ == 2
#include <t2na.p4>
#define PKTGEN_PORT1 6
#else
#include <tna.p4>
#define PKTGEN_PORT1 68
#endif

#include "common/headers.p4"
#include "common/util.p4"


#if __TARGET_TOFINO__ == 1
header tna_timestamps_h {
    bit<16> pad_1;
    bit<48> ingress_mac;
    bit<16> pad_2;
    bit<48> ingress_global;
    bit<16> pad_5;
    bit<48> egress_global;
    bit<16> pad_6;
    bit<48> egress_tx;
}
#else
header tna_timestamps_h {
    bit<16> pad_1;
    bit<48> ingress_mac;
    bit<16> pad_2;
    bit<48> ingress_global;
    bit<16> pad_5;
    bit<48> egress_global;
    bit<16> pad_6;
    bit<48> egress_tx;
}
#endif

typedef bit<32> ts_t;
typedef bit<16> dptp_type_t;
typedef bit<16> tor_id_t;
typedef bit<16> slice_t;

const dptp_type_t DPTP_PUSH_CLOCK = 16w0x0000;
const dptp_type_t DPTP_INIT = 16w0x0001;
const dptp_type_t DPTP_REQ = 16w0x0002;
const dptp_type_t DPTP_RESP = 16w0x0003;

const dptp_type_t DPTP_SM_MASTER = 16w0x0010;
const dptp_type_t DPTP_SM_CLIENT = 16w0x0011;

header dptp_h {
    dptp_type_t type;
    tor_id_t master_id;
    tor_id_t client_id;

    bit<16> req_tx_hi;
    bit<32> req_tx;

    bit<16> req_rx;

    //bit<32> resp_eg;
    bit<32> master_offset;

    bit<16> resp_tx_hi;
    bit<32> resp_tx;

    bit<32> resp_rx;
}


struct header_t {
    //pktgen_timer_header_t pktgen_timer;
    ethernet_h ethernet;
    vlan_tag_h vlan_tag;
    ipv4_h ipv4;
    ipv6_h ipv6;
    tcp_h tcp;
    udp_h udp;
    dptp_h dptp;

    // Add more headers here.
}

struct metadata_t {
    pktgen_timer_header_t pktgen_timer;
    tna_timestamps_h tna_timestamps_hdr;
    ptp_metadata_t tx_ptp_md_hdr;
}



// ---------------------------------------------------------------------------
// Ingress parser
// ---------------------------------------------------------------------------
parser IngressParser(
        packet_in pkt,
        out header_t hdr,
        out metadata_t ig_md,
        out ingress_intrinsic_metadata_t ig_intr_md) {

    TofinoIngressParser() tofino_parser;

    /*
    state start {
        tofino_parser.apply(pkt, ig_intr_md);
        transition parse_ethernet;
    }
    */

    state start {
        tofino_parser.apply(pkt, ig_intr_md);

        pktgen_timer_header_t pktgen_pd_hdr = pkt.lookahead<pktgen_timer_header_t>();
        transition select(pktgen_pd_hdr.app_id) {
            1 : parse_pktgen;
            2 : parse_pktgen;
            default : parse_ethernet;
        }
    }

    state parse_pktgen {
        pkt.extract(ig_md.pktgen_timer);
        transition select(ig_md.pktgen_timer.app_id) {
            1 : parse_ethernet;
            2 : accept;
        }
    }

    state parse_ethernet {
        pkt.extract(hdr.ethernet);
        transition select (hdr.ethernet.ether_type) {
            ETHERTYPE_IPV4 : parse_ipv4;
            default : reject;
        }
    }

    state parse_ipv4 {
        pkt.extract(hdr.ipv4);
        transition select(hdr.ipv4.protocol) {
            IP_PROTOCOLS_UDP : parse_udp;
            default : reject;
        }
    }

    state parse_udp {
        pkt.extract(hdr.udp);
        pkt.extract(hdr.dptp);
        transition accept;
    }

}



control Ingress(
        inout header_t hdr,
        inout metadata_t ig_md,
        in ingress_intrinsic_metadata_t ig_intr_md,
        in ingress_intrinsic_metadata_from_parser_t ig_intr_prsr_md,
        inout ingress_intrinsic_metadata_for_deparser_t ig_intr_dprsr_md,
        inout ingress_intrinsic_metadata_for_tm_t ig_intr_tm_md) {

        tor_id_t master_id;
        tor_id_t client_id;
        bit<8> sync_dst_index;
        bit<8> drift_update_index;
        bit<8> is_new_slice = 0;

        slice_t slice_id;

        DirectCounter<bit<32>>(CounterType_t.PACKETS) hit_counter;

        action set_port(bit<9> egress_port) {
            ig_intr_tm_md.ucast_egress_port = egress_port;
            hit_counter.count();
        }


        Register<bit<16>, bit<16>>(size = 1, initial_value = 0xff) db_reg;
        RegisterAction<bit<16>, bit<16>, bit<16>>(db_reg) db = {
            void apply(inout bit<16> value) {
                value = (bit<16>)hdr.ethernet.ether_type;
            }
        };

        Register<slice_t, slice_t>(size = 1, initial_value = 0x0) slice_reg;
        RegisterParam<slice_t>(1) slice_number;
        RegisterAction<slice_t, bit<8>, slice_t>(slice_reg) update_slice = {
            void apply(inout slice_t value, out slice_t rv) {
                if (value == slice_number.read()) {
                    value = 0;
                } else {
                    value = value + 1;
                }
                rv = value;
            }
        };

        RegisterAction<slice_t, bit<8>, slice_t>(slice_reg) read_slice = {
            void apply(inout slice_t value, out slice_t rv) {
                rv = value;
            }
        };

        DirectCounter<bit<32>>(CounterType_t.PACKETS) schedule_counter;

        action set_client(tor_id_t client) {
            hdr.dptp.client_id = client;
            schedule_counter.count();
        }

        table tb_check_sync_schedule {
            key = {
                hdr.dptp.type : exact@name("dptp_type");
                slice_id : exact;
                master_id   :   exact;
                sync_dst_index : exact;
            }
            actions = {
                set_client;
            }
            size = 16000;
            counters = schedule_counter;
        }

        action drop(bit<3> drop_bit) {
            ig_intr_dprsr_md.drop_ctl = drop_bit;
            db.execute(0);
            hit_counter.count();
        }

        table forward {
            key = {
                hdr.dptp.type : exact@name("dptp_type");
            }
            actions = {
                set_port;
                @defaultonly drop;
            }
            const default_action = drop(0x1);
            size = 32;
            counters = hit_counter;
        }

        action set_bg_port(bit<9> egress_port) {
            ig_intr_tm_md.ucast_egress_port = egress_port;
        }

        table forward_bg {
            key = {
                ig_md.pktgen_timer.app_id  : exact@name("app_id");
            }
            actions = {
                set_bg_port;
            }
            size = 32;
        }

        ts_t wire_delay = 0;
        ts_t drift = 0;

        ts_t master_ts = 0;
        ts_t offset = 0;
        ts_t sync_error = 0;

        DirectCounter<bit<32>>(CounterType_t.PACKETS) wire_delay_ctr;

        action read_wire_delay (ts_t input_wire_delay) {
            wire_delay = input_wire_delay;
            wire_delay_ctr.count();
        }

        table tb_read_wire_delay {
            key = {
                ig_intr_md.ingress_port : exact;
            }
            actions = {
                read_wire_delay;
            }
            size = 32;
            counters = wire_delay_ctr;
        }

        ts_t offset_stage1_tmp = 0;

        action cal_sm_offset_stage1(){
            offset_stage1_tmp = hdr.dptp.resp_tx + wire_delay;
        }

        action cal_sm_offset_stage2(){
            offset = offset_stage1_tmp - hdr.dptp.resp_rx;
        }

        action cal_sync_error() {
            sync_error = offset;
        }


        Register<ts_t, tor_id_t>(size = 512) offset_reg;
        RegisterAction<ts_t, tor_id_t, ts_t>(offset_reg) update_offset_reg = {
            void apply(inout ts_t value, out ts_t rv) {
                rv = value - offset; // Drift: offset difference from last time
                value = offset;
            }
        };

        RegisterAction<ts_t, tor_id_t, ts_t>(offset_reg) update_offset_with_drift_reg = {
            void apply(inout ts_t value, out ts_t rv) {
                value = value + drift;
                rv = value;
            }
        };

        RegisterAction<ts_t, tor_id_t, ts_t>(offset_reg) read_offset_reg = {
            void apply(inout ts_t value, out ts_t rv) {
                rv = value;
            }
        };

        Register<ts_t, bit<16>>(size = 1) offset_sample_reg;
        RegisterAction<ts_t, bit<16>, ts_t>(offset_sample_reg) record_offset_sample_reg = {
            void apply(inout ts_t value, out ts_t rv) {
                rv = value - offset; // Drift: offset difference from last time
                value = offset;
            }
        };

        action read_drift (ts_t simulated_drift) {
            drift = simulated_drift;
        }

        table tb_read_drift {
            key = {
                master_id : exact;
            }
            actions = {
                read_drift;
            }
            size = 1024;
        }


        Random<bit<4>>() random_16;
        bit<4> random_value = 0;

        action read_noise (ts_t noise_value) {
            drift = drift + noise_value;
        }

        table tb_add_noise_to_drift {
            key = {
                random_value : exact;
            }
            actions = {
                read_noise;
            }
            size = 16;
        }

        Register<ts_t, bit<16>>(size = 1) random_value_reg;
        RegisterAction<ts_t, bit<16>, ts_t>(random_value_reg) record_random_value = {
            void apply(inout ts_t value) {
                value = (ts_t)drift;
            }
        };
        
        
        Register<ts_t, bit<16>>(size = 4096) error_reg;
        RegisterAction<ts_t, bit<16>, ts_t>(error_reg) record_error_reg = {
            void apply(inout ts_t value) {
                value = hdr.dptp.master_offset;
            }
        };

        bit<16> index = 0;
        Register<bit<16>, bit<16>>(size = 1) index_reg;
        RegisterAction<bit<16>, bit<1>, bit<16>>(index_reg) incre_index_reg = {
            void apply(inout bit<16> value, out bit<16> rv) {
                if(value < 4096) {
                    value = value + 1;
                }
                else {
                    value = 0;
                }

                rv = value;
            }
        };
        RegisterAction<bit<16>, bit<1>, bit<16>>(index_reg) read_index_reg = {
            void apply(inout bit<16> value, out bit<16> rv) {

                rv = value;
            }
        };
        
        
        apply {
            
            if(hdr.dptp.isValid()) { //can't be removed! Else all packet would be forwarded.

            master_id = (tor_id_t)ig_md.pktgen_timer.batch_id;
            sync_dst_index = (bit<8>)ig_md.pktgen_timer.packet_id;
            //drift_update_index = (bit<8>)ig_md.pktgen_timer.packet_id;


            if(hdr.dptp.type == DPTP_SM_MASTER) {

                if (master_id == 0 && sync_dst_index == 0) {
                    is_new_slice = 8w1;
                }

                if (is_new_slice == 8w1) {
                    slice_id = update_slice.execute(0);
                    index = incre_index_reg.execute(0);
                } else {
                    slice_id = read_slice.execute(0);
                    index = read_index_reg.execute(0);
                }

                //Get drift for this ToR
                tb_read_drift.apply();
                random_value = random_16.get();
                if (master_id != 0) {
                    tb_add_noise_to_drift.apply();
                }
                record_random_value.execute(0);

                //Read master ToR's clock from the regesters.
                if (sync_dst_index == 0){
                    hdr.dptp.master_offset = update_offset_with_drift_reg.execute(master_id);
                    if (master_id == 6) {
                        record_error_reg.execute(index);
                    }
                } else {
                    hdr.dptp.master_offset = read_offset_reg.execute(master_id);
                }
                
                //Read sync schedule to decide who to sync with
                if(tb_check_sync_schedule.apply().hit){
                    forward.apply();
                }

            } else if(hdr.dptp.type == DPTP_SM_CLIENT) {
                //wire delay is profiled in advance.
                tb_read_wire_delay.apply();

                //Read rx
                hdr.dptp.resp_rx = (ts_t)ig_intr_md.ingress_mac_tstamp;
                //Apply offset to tx
                hdr.dptp.resp_tx = hdr.dptp.resp_tx + hdr.dptp.master_offset;

                cal_sm_offset_stage1();
                cal_sm_offset_stage2();
                
                update_offset_reg.execute(hdr.dptp.client_id);
                //cal_sync_error();
                //record_error_reg.execute(0);
            }
            /* else {
                ig_intr_tm_md.ucast_egress_port = 16;
            }
            */
            
            ig_intr_tm_md.qid = 0;
            }

            else if (ig_md.pktgen_timer.app_id == 2) {
                forward_bg.apply();
                ig_intr_tm_md.qid = 1;
            }

        }
}


// ---------------------------------------------------------------------------
// Ingress Deparser
// ---------------------------------------------------------------------------
control IngressDeparser(
        packet_out pkt,
        inout header_t hdr,
        in metadata_t ig_md,
        in ingress_intrinsic_metadata_for_deparser_t ig_intr_dprsr_md) {

    apply {
        pkt.emit(hdr);
    }
}

// ---------------------------------------------------------------------------
// Egress Parser
// ---------------------------------------------------------------------------
parser EgressParser(
        packet_in pkt,
        out header_t hdr,
        out metadata_t eg_md,
        out egress_intrinsic_metadata_t eg_intr_md) {

    TofinoEgressParser() tofino_parser;

    state start {
        tofino_parser.apply(pkt, eg_intr_md);
        transition parse_ethernet;
    }

    state parse_ethernet {
        pkt.extract(hdr.ethernet);
        transition select(hdr.ethernet.ether_type) {
            ETHERTYPE_IPV4 : parse_ipv4;
            default : reject;
        }
    }

    state parse_ipv4 {
        pkt.extract(hdr.ipv4);
        transition select(hdr.ipv4.protocol) {
            IP_PROTOCOLS_UDP : parse_udp;
            default : reject;
        }
    }

    state parse_udp {
        pkt.extract(hdr.udp);
        //If packet length is not enough to extract dptp header. Strange things happen
        pkt.extract(hdr.dptp);
        transition accept;
    }
}


// ---------------------------------------------------------------------------
// Egress 
// ---------------------------------------------------------------------------
control Egress(
        inout header_t hdr,
        inout metadata_t eg_md,
        in egress_intrinsic_metadata_t eg_intr_md,
        in egress_intrinsic_metadata_from_parser_t eg_intr_from_prsr,
        inout egress_intrinsic_metadata_for_deparser_t eg_intr_md_for_dprsr,
        inout egress_intrinsic_metadata_for_output_port_t eg_intr_md_for_oport) {


    Register<ts_t, bit<1>>(size = 1) eg_global_reg;
    RegisterAction<ts_t, bit<1>, ts_t>(eg_global_reg) record_eg_global_reg = {
        void apply(inout ts_t value) {
            value = (ts_t)eg_intr_from_prsr.global_tstamp;
        }
    };

    apply {

        if(hdr.dptp.type == DPTP_SM_MASTER){

            hdr.dptp.type = DPTP_SM_CLIENT;

            //hdr.dptp.resp_eg = (ts_t)eg_intr_from_prsr.global_tstamp;

            
            // request tx ptp correction timestamp insertion
            eg_intr_md_for_oport.update_delay_on_tx = 1w1;
            // Instructions for the ptp correction timestamp writer
            eg_md.tx_ptp_md_hdr.setValid();
            eg_md.tx_ptp_md_hdr.cf_byte_offset = 8w60; //RESPONSE tx timestamp
            eg_md.tx_ptp_md_hdr.udp_cksum_byte_offset = 8w40;
            eg_md.tx_ptp_md_hdr.updated_cf = 0;
            

        }

    }
}

// ---------------------------------------------------------------------------
// Egress Deparser
// ---------------------------------------------------------------------------
control EgressDeparser(packet_out pkt,
                              inout header_t hdr,
                              in metadata_t eg_md,
                              in egress_intrinsic_metadata_for_deparser_t 
                                eg_intr_dprsr_md
                              ) {

    apply {
        // tx timestamping is only available on hardware
        pkt.emit(eg_md.tx_ptp_md_hdr);
        pkt.emit(hdr);
    }
}


Pipeline(IngressParser(),
         Ingress(),
         IngressDeparser(),
         EgressParser(),
         Egress(),
         EgressDeparser()) pipe;
         
Switch(pipe) main;
