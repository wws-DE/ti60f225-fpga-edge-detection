`timescale 1ns/1ps
module tb_context_chain;
    parameter integer W=40,H=12,DROP=16,T=64;
    localparam integer N=W*H/2;
    reg clk=0;always #5 clk=~clk;
    reg rst=1,start=0,flush=0,iv=0,ordy=1;
    reg [83:0] input_data=0;
    reg [10:0] ix=0,iy=0;
    reg isof=0,ieol=0,ieof=0;
    wire ir,pv,pr,wv,wr,ov,pe,we,fe;
    wire [31:0] pp;
    wire [287:0] ww;
    wire [24:0] pc,wc,oc;
    wire [15:0] center;
    wire [1:0] edge_pair;
    reg [83:0] source_data[0:N-1];
    reg [49:0] golden[0:N-1];
    integer accepted=0,delivered=0,packed_count=0,stalls=0,cycles=0;
    reg [31:0] random_state=431;
    reg [42:0] held_data;
    reg held;
    string ipath,gpath;
    edge_context_pack_pair #(.THRESHOLD_DROP(DROP)) pack(
        .clk(clk),.rst(rst),.frame_start(start),.data_flush(flush),.in_valid(iv),.in_ready(ir),
        .in_center_pair(input_data[83:68]),.in_gx_pair(input_data[67:46]),
        .in_gy_pair(input_data[45:24]),.in_l1_pair(input_data[23:2]),.in_seed_pair(input_data[1:0]),
        .threshold(11'(T)),.in_x_even(ix),.in_y(iy),.in_sof(isof),.in_eol(ieol),.in_eof(ieof),
        .out_valid(pv),.out_ready(pr),.out_pair(pp),.out_x_even(pc[10:0]),.out_y(pc[21:11]),
        .out_sof(pc[22]),.out_eol(pc[23]),.out_eof(pc[24]),.empty(pe));
    edge_context_window_pair #(.W(W),.H(H)) window(
        .clk(clk),.rst(rst),.frame_start(start),.data_flush(flush),.in_valid(pv),.in_ready(pr),.in_pair(pp),
        .in_x_even(pc[10:0]),.in_y(pc[21:11]),.in_sof(pc[22]),.in_eol(pc[23]),.in_eof(pc[24]),
        .out_valid(wv),.out_ready(wr),.out_window_pair(ww),.out_x_even(wc[10:0]),.out_y(wc[21:11]),
        .out_sof(wc[22]),.out_eol(wc[23]),.out_eof(wc[24]),.empty(we));
    edge_context_filter_pair #(.W(W),.H(H)) filter(
        .clk(clk),.rst(rst),.frame_start(start),.data_flush(flush),.in_valid(wv),.in_ready(wr),.in_window_pair(ww),
        .in_x_even(wc[10:0]),.in_y(wc[21:11]),.in_sof(wc[22]),.in_eol(wc[23]),.in_eof(wc[24]),
        .out_valid(ov),.out_ready(ordy),.out_center_pair(center),.out_edge_pair(edge_pair),
        .out_x_even(oc[10:0]),.out_y(oc[21:11]),.out_sof(oc[22]),.out_eol(oc[23]),.out_eof(oc[24]),.empty(fe));
    always @(posedge clk)begin
        held=0;
        if(rst||start||flush)begin accepted=0;delivered=0;packed_count=0;end
        else begin
            if(iv&&ir)accepted=accepted+1;
            if(pv&&pr)begin
                if(pp!==golden[packed_count][49:18])$fatal(1,"Pack mismatch %0d",packed_count);
                if(pc!=={packed_count==N-1,packed_count%(W/2)==W/2-1,packed_count==0,
                    11'(packed_count/(W/2)),11'((packed_count%(W/2))*2)})$fatal(1,"Pack identity");
                packed_count=packed_count+1;
            end
            if(ov)begin
                if(delivered>=N)$fatal(1,"Extra output");
                if({center,edge_pair}!==golden[delivered][17:0])
                    $fatal(1,"Context mismatch index=%0d got=%h want=%h",delivered,{center,edge_pair},golden[delivered][17:0]);
                if(oc!=={delivered==N-1,delivered%(W/2)==W/2-1,delivered==0,
                    11'(delivered/(W/2)),11'((delivered%(W/2))*2)})$fatal(1,"Output identity");
                if(ordy)delivered=delivered+1;
                else begin held=1;held_data={oc,center,edge_pair};stalls=stalls+1;end
            end
        end
        #1;if(held&&(ov!==1||{oc,center,edge_pair}!==held_data))$fatal(1,"Output changed during stall");
    end
    task launch;
        @(negedge clk);iv=0;ordy=1;start=1;
        @(negedge clk);start=0;
    endtask
    task feed(input integer count,input integer stress);
        integer sent;
        reg blocked;
        begin
            sent=0;cycles=0;blocked=0;
            while(sent<count)begin
                @(negedge clk);random_state=random_state*32'd1664525+32'd1013904223;
                ordy=!stress||(random_state[3:0]>3);
                if(stress&&cycles>=30&&cycles<70)ordy=0;
                if(!blocked)iv=!stress||random_state[7:4]>2;
                input_data=source_data[sent];ix=(sent%(W/2))*2;iy=sent/(W/2);
                isof=sent==0;ieol=sent%(W/2)==W/2-1;ieof=sent==N-1;
                @(posedge clk);blocked=iv&&!ir;if(iv&&ir)sent=sent+1;
                #2;cycles=cycles+1;if(cycles>count*15+1000)$fatal(1,"Feed timeout");
            end
            @(negedge clk);iv=0;ordy=1;
        end
    endtask
    task drain;
        integer wait_count;
        begin
            wait_count=0;
            while(!(pe&&we&&fe))begin @(negedge clk);wait_count=wait_count+1;
                if(wait_count>N+100)$fatal(1,"Drain timeout");end
            if(accepted!=N||delivered!=N||packed_count!=N)$fatal(1,"Frame accounting %0d/%0d/%0d",accepted,delivered,packed_count);
        end
    endtask
    initial begin
        if(!$value$plusargs("INPUT=%s",ipath)||!$value$plusargs("GOLD=%s",gpath))$fatal(1,"Paths missing");
        $readmemh(ipath,source_data);$readmemh(gpath,golden);
        repeat(4)@(negedge clk);rst=0;
        launch();feed(N,0);drain();
        launch();feed(N,1);drain();
        for(integer kind=0;kind<3;kind=kind+1)begin
            launch();feed(W/2+4,0);
            @(negedge clk);if(kind==0)flush=1;else if(kind==1)start=1;else rst=1;
            @(posedge clk);#2;if(ov)$fatal(1,"Interrupt output leak");
            @(negedge clk);flush=0;start=0;rst=0;
            launch();feed(N,0);drain();
        end
        $display("CONTEXT_CHAIN_PASS W=%0d H=%0d DROP=%0d T=%0d frames=5 interrupts=3 stalls=%0d",W,H,DROP,T,stalls);
        $finish;
    end
endmodule
