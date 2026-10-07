/** The experimental LAI scale has no validated health interpretation. */
export default function LAIHealthCard(_props: { data: any }) {
  return (
    <div className="lf-card" style={{ padding: 20, marginBottom: 16 }}>
      <h3 style={{ margin: '0 0 8px' }}>学习记录</h3>
      <p style={{ margin: 0 }}>此版本暂不提供学习健康评分。你可以在练习记录中查看作答次数、正确率和用时。</p>
    </div>
  );
}
