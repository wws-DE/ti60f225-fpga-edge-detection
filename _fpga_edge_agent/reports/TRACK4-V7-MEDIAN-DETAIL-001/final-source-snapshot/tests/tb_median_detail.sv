module tb_median_detail;
    parameter integer N=12000,W=40,H=12;
    reg clk=0;always #5 clk=~clk;
    reg rst=1,frame_start=0,flush=0,in_valid=0,out_ready=0,median_enable=1,detail_enable=1;
    wire in_ready,out_valid,empty,legacy_ready,legacy_valid,legacy_empty;
    reg [169:0] inputs[0:N-1];reg[31:0] gold[0:N-1];
    integer index=0;wire[169:0] value=inputs[index];
    wire[15:0] actual,legacy;wire[10:0] ox,oy,lx,ly;
    wire os,ol,oe,ls,ll,le;
    median9_detail_pair #(.W(W),.H(H)) dut(.clk(clk),.rst(rst),.frame_start(frame_start),.flush(flush),
        .in_valid(in_valid),.in_ready(in_ready),.in_window_pair(value[143:0]),.median_enable(median_enable),
        .detail_enable(detail_enable&&value[169]),.in_x_even(value[154:144]),.in_y(value[165:155]),
        .in_sof(value[166]),.in_eol(value[167]),.in_eof(value[168]),.out_valid(out_valid),.out_ready(out_ready),
        .out_y_pair(actual),.out_x_even(ox),.out_y(oy),.out_sof(os),.out_eol(ol),.out_eof(oe),.empty(empty));
    median9_pair original(.clk(clk),.rst(rst),.frame_start(frame_start),.flush(flush),.in_valid(in_valid),
        .in_ready(legacy_ready),.in_window_pair(value[143:0]),.median_enable(median_enable),
        .in_x_even(value[154:144]),.in_y(value[165:155]),.in_sof(value[166]),.in_eol(value[167]),.in_eof(value[168]),
        .out_valid(legacy_valid),.out_ready(out_ready),.out_y_pair(legacy),.out_x_even(lx),.out_y(ly),
        .out_sof(ls),.out_eol(ll),.out_eof(le),.empty(legacy_empty));
    reg [56:0] queue[0:2*N];integer written=0,read_at=0,checks=0,cancels=0,stalls=0,restored=0;
    reg accepted_last=0,was_stalled=0;reg[40:0] held;
    reg[15:0] expected,expected_legacy;reg[24:0] metadata;
    always @(posedge clk)begin
        accepted_last=0;
        if(rst||frame_start||flush)begin written=0;read_at=0;was_stalled=0;end
        else begin
            if({in_ready,out_valid,empty}!={legacy_ready,legacy_valid,legacy_empty})$fatal(1,"protocol differs");
            if(was_stalled && ({oe,ol,os,oy,ox,actual}!==held))$fatal(1,"stalled output changed");
            was_stalled=out_valid&&!out_ready;held={oe,ol,os,oy,ox,actual};
            if(was_stalled)stalls=stalls+1;
            if(out_valid&&out_ready)begin
                if(read_at>=written)$fatal(1,"unexpected output");
                {metadata,expected,expected_legacy}=queue[read_at];
                if({oe,ol,os,oy,ox}!==metadata||{le,ll,ls,ly,lx}!==metadata||actual!==expected||legacy!==expected_legacy)
                    $fatal(1,"median compare output=%0d actual=%h expected=%h legacy=%h expectedold=%h",read_at,actual,expected,legacy,expected_legacy);
                if(actual!=legacy)restored=restored+1;
                read_at=read_at+1;checks=checks+1;
            end
            if(in_valid&&in_ready)begin
                expected_legacy=median_enable?gold[index][15:0]:{value[111:104],value[39:32]};
                expected=(median_enable&&detail_enable)?gold[index][31:16]:expected_legacy;
                queue[written]={value[168:144],expected,expected_legacy};written=written+1;accepted_last=1;
            end
        end
    end
    task automatic job(input integer count,cutoff);
        integer cursor,cycle,begin_written,begin_read;
        begin
            cursor=0;cycle=0;in_valid=0;begin_written=written;begin_read=read_at;
            while(cycle<20*N)begin
                @(negedge clk);
                if(accepted_last)cursor=cursor+1;
                if(!(in_valid&&!accepted_last))begin
                    if(cursor<count)begin index=cursor;in_valid=(cycle%7!=0);end
                    else in_valid=0;
                end
                out_ready=(cycle%19>3)&&!(cycle>=100&&cycle<150);
                cycle=cycle+1;
                if(cutoff!=0&&cursor>=cutoff)begin in_valid=0;break;end
                if(cursor==count&&empty&&!in_valid)break;
            end
            if(cycle>=20*N)$fatal(1,"job timeout");
            if(cutoff==0&&(written-begin_written!=count||read_at-begin_read!=count))$fatal(1,"count mismatch %0d %0d expected%0d",written,read_at,count);
        end
    endtask
    task automatic abort_pipeline(input integer kind);
        begin
            @(negedge clk);in_valid=0;out_ready=0;
            if(kind==0)flush=1;else if(kind==1)frame_start=1;else rst=1;
            repeat(2)@(negedge clk);
            flush=0;frame_start=0;rst=0;cancels=cancels+1;
        end
    endtask
    string ip,gp;
    initial begin
        if(!$value$plusargs("INPUT=%s",ip)||!$value$plusargs("GOLD=%s",gp))$fatal(1,"vectors missing");
        $readmemh(ip,inputs);$readmemh(gp,gold);
        repeat(3)@(negedge clk);rst=0;
        job(N,0);
        for(integer kind=0;kind<3;kind=kind+1)begin job(100,73);abort_pipeline(kind);job(160,0);end
        @(negedge clk);median_enable=0;job(512,0);
        @(negedge clk);median_enable=1;detail_enable=0;job(512,0);
        if(checks<N||restored==0||stalls==0||cancels!=3)$fatal(1,"insufficient coverage");
        $display("MEDIAN_DETAIL_PASS N=%0d W=%0d H=%0d checks=%0d restored=%0d stalls=%0d cancels=%0d",N,W,H,checks,restored,stalls,cancels);$finish;
    end
endmodule
