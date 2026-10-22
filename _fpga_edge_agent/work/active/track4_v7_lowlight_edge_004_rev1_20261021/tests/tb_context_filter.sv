`timescale 1ns/1ps
module tb_context_filter;
    parameter integer N=100,W=40,H=12;
    reg clk=0;always #5 clk=~clk;
    reg rst=1,start=0,flush=0,iv=0,ordy=1;
    reg [287:0] window_pair=0;
    reg [10:0] x=0,y=0;
    wire ir,ov,empty;
    wire [15:0] center;
    wire [1:0] edges;
    wire [24:0] coord;
    reg [327:0] records[0:N-1]; // window288, x11,y11, expected18
    integer ids[0:1],tag=0,checks=0,stalls=0;
    reg [1:0] valid=0;
    string path;
    edge_context_filter_pair #(.W(W),.H(H)) dut(
        .clk(clk),.rst(rst),.frame_start(start),.data_flush(flush),.in_valid(iv),.in_ready(ir),
        .in_window_pair(window_pair),.in_x_even(x),.in_y(y),.in_sof(tag==0),.in_eol(tag%20==19),.in_eof(tag==N-1),
        .out_valid(ov),.out_ready(ordy),.out_center_pair(center),.out_edge_pair(edges),
        .out_x_even(coord[10:0]),.out_y(coord[21:11]),.out_sof(coord[22]),.out_eol(coord[23]),.out_eof(coord[24]),.empty(empty));
    always @(posedge clk)begin
        if(rst||start||flush)valid=0;
        else if(!valid[1]||ordy)begin valid={valid[0],iv};ids[1]=ids[0];ids[0]=tag;end
        else stalls=stalls+1;
        #1;
        if(ov!==valid[1])$fatal(1,"Two-stage valid");
        if(ov)begin
            if({center,edges}!==records[ids[1]][17:0])$fatal(1,"Filter numeric id=%0d",ids[1]);
            if(coord!=={ids[1]==N-1,ids[1]%20==19,ids[1]==0,records[ids[1]][28:18],records[ids[1]][39:29]})$fatal(1,"Filter identity");
            checks=checks+1;
        end
    end
    initial begin
        if(!$value$plusargs("DATA=%s",path))$fatal(1,"DATA missing");$readmemh(path,records);
        repeat(4)@(negedge clk);rst=0;
        for(integer sent=0;sent<N;)begin
            @(negedge clk);iv=1;ordy=!(sent%31==0&&stalls<40);
            tag=sent;window_pair=records[sent][327:40];x=records[sent][39:29];y=records[sent][28:18];
            @(posedge clk);if(iv&&ir)sent=sent+1;#2;
        end
        @(negedge clk);iv=0;ordy=1;
        repeat(5)@(negedge clk);
        if(!empty)$fatal(1,"Filter not empty");
        $display("CONTEXT_FILTER_PASS vectors=%0d checks=%0d stalls=%0d",N,checks,stalls);$finish;
    end
endmodule
