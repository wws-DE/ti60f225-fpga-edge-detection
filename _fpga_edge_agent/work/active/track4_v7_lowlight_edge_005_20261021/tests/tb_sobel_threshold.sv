`timescale 1ns/1ps
module tb_sobel_threshold;
    parameter N=20;
    reg clk=0;always #5 clk=~clk;
    reg rst=1,valid=0;
    reg [143:0] win=0;
    reg [10:0] threshold=96,x=0;
    wire ready,ov,empty;
    wire [1:0] edge_pair;
    wire [15:0] center;
    wire [21:0] gx,gy,l1;
    wire [10:0] ox,oy;
    wire sof,eol,eof;
    // 记录：window144 / center16 / gx22 / gy22 / l1 22 / edge2。
    reg [227:0] records[0:N-1];
    string path;
    integer sent=0,received=0,i;
    sobel_pair dut(.clk(clk),.rst(rst),.frame_start(1'b0),.flush(1'b0),
        .in_valid(valid),.in_ready(ready),.in_window_pair(win),.output_kind(2'd1),.threshold(threshold),
        .in_x_even(x),.in_y(11'd7),.in_sof(1'b0),.in_eol(1'b0),.in_eof(1'b0),
        .out_valid(ov),.out_ready(1'b1),.out_y_pair(center),.out_edge(edge_pair),
        .out_gx_pair(gx),.out_gy_pair(gy),.out_l1_pair(l1),.out_x_even(ox),.out_y(oy),
        .out_sof(sof),.out_eol(eol),.out_eof(eof),.empty(empty));
    always @(posedge clk)begin
        #1;
        if(!rst&&ov)begin
            if(received>=N)$fatal(1,"Extra output");
            if({center,gx,gy,l1,edge_pair}!==records[received][83:0])
                $fatal(1,"Sobel item=%0d got=%h want=%h",received,{center,gx,gy,l1,edge_pair},records[received][83:0]);
            if(ox!==received*2||oy!==7||sof||eol||eof)$fatal(1,"Pixel identity");
            received=received+1;
        end
    end
    initial begin
        if(!$value$plusargs("DATA=%s",path))$fatal(1,"Missing data");
        if(!$value$plusargs("THRESHOLD=%d",threshold))$fatal(1,"Missing threshold");
        $readmemh(path,records);
        repeat(4)@(negedge clk);rst=0;
        for(i=0;i<N;i=i+1)begin
            @(negedge clk);valid=1;win=records[i][227:84];x=i*2;
            if(!ready)$fatal(1,"Unexpected backpressure");
            sent=sent+1;
        end
        @(negedge clk);valid=0;
        repeat(10)@(negedge clk);
        if(received!=N||!empty)$fatal(1,"Missing output %0d",received);
        $display("SOBEL_THRESHOLD_PASS threshold=%0d pairs=%0d lanes=%0d",threshold,received,received*2);
        $finish;
    end
endmodule
