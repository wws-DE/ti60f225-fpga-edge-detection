`timescale 1ns/1ps
module tb_coherent_sobel;
    parameter integer N=100,ENABLE=1,D=18,DROP=0,T=64,KIND=1;
    reg clk=0;always #5 clk=~clk;
    reg rst=1,start=0,flush=0,valid=0,out_ready=1;
    reg [143:0] win=0;
    reg [10:0] x=0,y=0;
    reg sof=0,eol=0,eof=0;
    wire ready,ov,empty,br,bv,be;
    wire [15:0] center,bc;
    wire [21:0] gx,gy,l1,bgx,bgy,bl1;
    wire [1:0] edges,bedges;
    wire [10:0] ox,oy,bx,by;
    wire os,ol,oe,bs,bl,bend;
    reg [227:0] records[0:N-1];
    integer input_tag=0,ids[0:5],sent,cycles,phase_delivered;
    integer accepted=0,delivered=0,discarded=0,checks=0,stalls=0,interrupts=0;
    reg [5:0] expected_valid=0;
    reg advance;
    reg [31:0] random_state=431;
    string path;
    sobel_pair #(.COHERENCE_ENABLE(1),.COHERENCE_MIN_DIFF(20),
        .WEAK_ENABLE(ENABLE),.WEAK_MIN_DIFF(D),.WEAK_THRESHOLD_DROP(DROP)) dut(
        .clk(clk),.rst(rst),.frame_start(start),.flush(flush),.in_valid(valid),.in_ready(ready),
        .in_window_pair(win),.output_kind(2'(KIND)),.threshold(11'(T)),
        .in_x_even(x),.in_y(y),.in_sof(sof),.in_eol(eol),.in_eof(eof),
        .out_valid(ov),.out_ready(out_ready),.out_y_pair(center),.out_edge(edges),
        .out_gx_pair(gx),.out_gy_pair(gy),.out_l1_pair(l1),.out_x_even(ox),.out_y(oy),
        .out_sof(os),.out_eol(ol),.out_eof(oe),.empty(empty));
    sobel_pair_baseline #(.COHERENCE_ENABLE(1),.COHERENCE_MIN_DIFF(20)) legacy(
        .clk(clk),.rst(rst),.frame_start(start),.flush(flush),.in_valid(valid),.in_ready(br),
        .in_window_pair(win),.output_kind(2'(KIND)),.threshold(11'(T)),
        .in_x_even(x),.in_y(y),.in_sof(sof),.in_eol(eol),.in_eof(eof),
        .out_valid(bv),.out_ready(out_ready),.out_y_pair(bc),.out_edge(bedges),
        .out_gx_pair(bgx),.out_gy_pair(bgy),.out_l1_pair(bl1),.out_x_even(bx),.out_y(by),
        .out_sof(bs),.out_eol(bl),.out_eof(bend),.empty(be));
    always @(posedge clk)begin
        if(rst||start||flush)begin
            for(integer i=0;i<6;i=i+1)if(expected_valid[i])discarded=discarded+1;
            expected_valid=0;
        end else begin
            if(valid&&ready)accepted=accepted+1;
            if(ov&&out_ready)delivered=delivered+1;
            advance=!expected_valid[5]||out_ready;
            if(advance)begin
                expected_valid={expected_valid[4:0],valid};
                for(integer i=5;i>0;i=i-1)ids[i]=ids[i-1];
                ids[0]=input_tag;
            end else stalls=stalls+1;
        end
        #1;
        if(ov!==expected_valid[5])$fatal(1,"Six-stage valid timing");
        if({ready,ov,empty}!=={br,bv,be})$fatal(1,"Legacy handshake changed");
        if(ov)begin
            if({center,gx,gy,l1,edges}!==records[ids[5]][83:0])
                $fatal(1,"Numeric id=%0d D=%0d enabled=%0d got=%h want=%h",ids[5],D,ENABLE,{center,gx,gy,l1,edges},records[ids[5]][83:0]);
            if(ox!==11'((ids[5]*2)%1920)||oy!==11'((ids[5]/960)%1080)||
               os!==(ids[5]==0)||ol!==(ids[5]%16==15)||oe!==(ids[5]==N-1))$fatal(1,"Identity");
            if({center,gx,gy,l1,ox,oy,os,ol,oe}!=={bc,bgx,bgy,bl1,bx,by,bs,bl,bend})$fatal(1,"Legacy diagnostics changed");
            if((bedges & ~edges)!=0)$fatal(1,"v2 edge lost");
            if(!ENABLE&&edges!==bedges)$fatal(1,"Disabled edge changed");
            checks=checks+1;
        end
    end
    task feed(input integer count,input integer stress);
        begin
            sent=0;cycles=0;
            while(sent<count)begin
                @(negedge clk);
                random_state=random_state*32'd1664525+32'd1013904223;
                out_ready=!stress||(random_state[3:0]>3);
                if(stress&&cycles>=10&&cycles<42)out_ready=0;
                valid=!stress||random_state[7:4]>2;
                input_tag=sent;win=records[sent][227:84];
                x=(sent*2)%1920;y=(sent/960)%1080;sof=sent==0;eol=sent%16==15;eof=sent==N-1;
                @(posedge clk);if(valid&&ready)sent=sent+1;
                #2;cycles=cycles+1;
                if(cycles>count*8+1000)$fatal(1,"Feed timeout");
            end
        end
    endtask
    task drain;
        @(negedge clk);valid=0;out_ready=1;
        repeat(10)begin @(posedge clk);#2;end
        if(!empty)$fatal(1,"Not drained");
    endtask
    initial begin
        if(!$value$plusargs("DATA=%s",path))$fatal(1,"DATA missing");
        $readmemh(path,records);
        repeat(4)@(negedge clk);rst=0;
        for(integer kind=0;kind<3;kind=kind+1)begin
            feed(13,0);
            @(negedge clk);valid=0;
            if(kind==0)flush=1;else if(kind==1)start=1;else rst=1;
            @(posedge clk);#2;if(ov||!empty)$fatal(1,"Interrupt failed");
            @(negedge clk);flush=0;start=0;rst=0;interrupts=interrupts+1;
        end
        phase_delivered=delivered;feed(N,0);drain();
        if(delivered-phase_delivered!=N)$fatal(1,"Normal output count");
        phase_delivered=delivered;feed(N<2048?N:2048,1);drain();
        if(delivered-phase_delivered!=(N<2048?N:2048))$fatal(1,"Stress output count");
        if(accepted!=delivered+discarded||stalls<20||interrupts!=3)$fatal(1,"Accounting/stress coverage");
        $display("COHERENT_SOBEL_PASS enabled=%0d D=%0d T=%0d vectors=%0d accepted=%0d delivered=%0d flushed=%0d stalls=%0d checks=%0d",ENABLE,D,T,N,accepted,delivered,discarded,stalls,checks);
        $finish;
    end
endmodule
